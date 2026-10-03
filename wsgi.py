# flake8: noqa
import random

from gevent import monkey
from sqlalchemy import update

monkey.patch_all()

import json
import threading
from add_extensions import redis_2, redis_4
from core import create_app, socketio, db
from dotenv import load_dotenv
from models import *
from models.bookings import (
    BookingStatusEnum, BookingContractDurationEnum, 
    BookingContract
)
from utils import get_class_by_tablename, load_env
from loguru import logger
from google.cloud import secretmanager
from google import auth
import click
import os
import shlex
import sys
import base64
import firebase_admin

load_dotenv()

ENV = os.getenv("APP_ENV", "DEV")
app = create_app(ENV.lower() if ENV else "default")
cred = firebase_admin.credentials.Certificate(app.config["F_KEY_PATH"])
firebase_admin.initialize_app(cred)

# test config
COV = None

if app.config["FLASK_COVERAGE"]:
    import coverage

    COV = coverage.Coverage(branch=True, source=["core/", "models/", "schemas/"])
    # COV.
    COV.start()

print(os.environ.get("DATABASE_URL"))
print(app.config)


# flask shell
@app.shell_context_processor
def make_shell_context():
    return dict(
        app=app, role=Role, user=User, artisan=Artisan, bk_cat=BookingCategory, db=db
    )


# flask cli commands
@app.cli.command()
def create_categories():
    """creates job categories in db"""
    print("Creating categories::", end="\n")
    BookingCategory.create_categories()
    print("Done!")


@app.cli.command("reset_user_bookings")
@click.argument("customer_id")
def reset_user_bookings(
    customer_id,
    target_status=random.choice([
        BookingStatusEnum.ARTISAN_CANCELLED,
        BookingStatusEnum.ARTISAN_MATCHED,
        BookingStatusEnum.COMPLETED
    ])
):
    """
    Data fix helper: Clears the 'active' booking limit for a test user
    by transitioning their open bookings to a closed state.
    """
    sess = db.session()
    stmt = (
        update(Booking)
        .where(
            Booking.customer_id == customer_id,
            Booking.status.in_(
                [BookingStatusEnum.IN_PROGRESS, BookingStatusEnum.PENDING]
            ),
        )
        .values(status=target_status)
    )

    result = sess.execute(stmt)
    sess.commit()

    print(
        f"Data fix complete: Updated {result.rowcount} bookings to {target_status.name} for user {customer_id}"
    )

@app.cli.command("force_start_contract_booking")
@click.argument("booking_id")
@click.argument("duration")
@click.argument("duration_unit_str")
def force_start_contract_booking(booking_id, duration, duration_unit_str):
    """
    Data fix helper: Converts an existing booking to a contract and 
    forces its state to IN_PROGRESS.
    """
    sess = db.session()
    # 1. Fetch the booking
    bk = sess.query(Booking).get(booking_id)
    if not bk:
        print(f"Error: Booking {booking_id} not found.")
        return

    # 2. Flag as a contract
    bk.contract_type = True
    
    # 3. Create and attach the contract if it doesn't exist
    if not bk.booking_contract:
        try:
            unit_enum = BookingContractDurationEnum[duration_unit_str.upper()]
        except KeyError:
            print(f"Error: Invalid duration unit '{duration_unit_str}'. Use 'DAYS' or 'WEEKS'.")
            return

        new_contract = BookingContract(
            duration=duration,
            duration_unit=unit_enum
        )
        bk.booking_contract = new_contract
        sess.add(new_contract)
        sess.flush() 

    # 4. Force transition to IN_PROGRESS and generate Work Sessions
    if bk.status != BookingStatusEnum.IN_PROGRESS:
        bk.start_booking(sess)
    sess.commit()
    print(f"Success: Booking {booking_id} is now IN_PROGRESS as a {duration}-{duration_unit_str} contract.")
# purge table
@app.cli.command()
@click.option("--table_name", help="specify name of table to be deleted")
def purge(table_name):
    """removes all rows in specified table"""
    model = get_class_by_tablename(table_name)
    model.query.delete()
    db.session.commit()
    print("completed purge on table {}".format(table_name))


# create user roles
@app.cli.command()
def create_roles():
    print(":: creating roles ::", end="\n")
    user_models.Role.insert_roles()
    print("completed !")


@app.cli.command()
@click.option("--role_name", help="specify name of role to be updated")
@click.option("--perm_value", help="specify value of permission to be added")
def update_role_permissions(role, perm):
    print(f"To add permission with value {perm} to role {role}")
    user_models.Role.updateRolePermissions(role, perm)
    print("Completed operation!")


@app.cli.command()
@click.option(
    "--coverage/--no-coverage", default=False, help="Run tests under coverage"
)
def test(coverage):
    """Run the unit tests"""
    # if not coverage and not app.config['FLASK_COVERAGE']:
    #     app.config['FLASK_COVERAGE'] = True
    #     # os.execvp(sys.executable, [sys.executable] + sys.argv)
    #     return
    import unittest

    test = unittest.TestLoader().discover("tests")
    unittest.TextTestRunner(verbosity=2).run(test)
    if COV and coverage:
        COV.stop()
        COV.save()
        print("Coverage Summary: ")
        COV.report()
        basedir = os.path.abspath(os.path.dirname(__file__))
        print(basedir)
        covdir = os.path.join(basedir, "tmp/coverage")
        COV.html_report(directory=covdir)
        print("HTML version: file://%s/index.html" % covdir)
        COV.erase()


@app.cli.command()
def load_config_variables():
    """fetches secrets from GCP secret manager and loads them into .env"""

    def gen_pairs(obj):
        val = base64.b64decode(obj["payload"]["data"]).decode("utf-8")
        yield f"{shlex.quote(obj['name'].split('/')[-3])}={shlex.quote(val)}"

    access_token = None
    keys = load_env(gen_pairs)

    if keys:
        try:
            with open(".env", "w") as file:
                for kv in keys:
                    file.write(kv)
                    file.write("\n")
            print("Written config secrets to .env")
        except Exception as e:
            print("Something went wrong while writing to .env")
            raise e
    else:
        raise Exception("Something went wrong while trying to fetch secrets")


def redis_dispatch_listener(socketio_instance):
    """
    Listens for 'dispatch' messages from the Background Worker
    and forwards them to specific SocketIO rooms.
    """
    from utils import send_notification
    from schemas import NewBookingRequestSchema
    from core.api.bookings.utils import parse_str_data

    pubsub = redis_2.pubsub()
    pubsub.subscribe("socket_server_dispatch")

    print("Redis Dispatch Listener Started...")

    for message in pubsub.listen():
        if message["type"] == "message":
            try:
                payload = parse_str_data(message.pop("data"))
                schema = NewBookingRequestSchema()
                bk_data = payload.pop("data")
                customer = bk_data.pop("user")
                lat, lon = bk_data.pop("lat"), bk_data.pop("lon")
                sid = redis_4.hget("user_to_sid", payload["target_id"])
                data = schema.load(
                    {
                        **bk_data,
                        "userDetails": customer,
                        "coordinates": {"lat": lat, "lon": lon},
                    }
                )
                socketio.emit("new_offer", data, to=sid, namespace="/artisan")
                notification_payload = {k: json.dumps(v) for k, v in data.items()}
                fcm_token = redis_4.hget("user_to_fcm_token", payload["target_id"])
                send_notification(
                    notification_payload,
                    fcm_token,
                    notification_object={
                        "body": "A client near you needs your service",
                        "title": "New Service Request Alert! 🚨",
                    },
                )
            except Exception as e:
                logger.exception(e)
                print(f"Dispatch Error: {e}")


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, debug=True, use_reloader=True)
