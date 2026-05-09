import json
import time
import datetime

from add_extensions import (
    HueyTemplate,
    redis_5,
    redis_2,
    redis_4,
    redis_6,
    redis_,
    redis_7,
)
from core.exc import BookingHasContract

# from core.extensions import db
from config import BaseConfig
from models.user_models import Artisan
from models.bookings import Booking, BookingContract, BookingStatusEnum, SettlementEnum
from tasks.exc import InvalidBookingTransaction
from models.payments import Payment
from schemas.bookings_schema import BookingSchema
from utils import setLogger
from config import config_options


import uuid
import logging
from loguru import logger
from huey import Huey
from flask import url_for


logging.basicConfig(level=logging.DEBUG)

# huey instance
huey: Huey = HueyTemplate(config=BaseConfig.HUEY_CONFIG).huey
logging.getLogger("huey").setLevel(logging.DEBUG)

setLogger()

# TODO: subclass decorator to include app context


@huey.task()
@huey.lock_task("lock_broadcast_task")
def pbq(booking_details, attempt_level=1):
    from tasks.events import send_event
    # check if a match has been found
    is_available = redis_.exists(booking_details['booking_id'])
    if not is_available:
        # do nothing
        return
    lat, lon = booking_details["lat"], booking_details["lon"]
    category = booking_details["job_category"]

    if attempt_level == 1:
        radius_km = 1
        min_rating = 4.8
    else:
        radius_km = 3
        min_rating = 3.75

    candidates = redis_5.georadius(
        category, lon, lat, radius_km, unit="km", withdist=True
    )
    if not candidates:
        # Retry with wider net if nobody found
        if attempt_level < 2:
            pbq.schedule((booking_details, attempt_level + 1), delay=5)
        else:
            # inform customer that no artisan is available to handle request
            payload = {
                'payload': {
                    'message': "No handymen found at this moment, please try again later."
                },
                'recipient': booking_details['user']['user_id']
            }
            send_event('no_available_handees', payload, '/customer')
        return

    artisan_ids = [c[0] for c in candidates]
    ratings = redis_6.hmget("artisan_ratings", artisan_ids)

    targeted_artisans = []

    for i, artisan_id in enumerate(artisan_ids):
        r_val = float(ratings[i]) if ratings[i] else 0.0
        # filter based on current min-rating
        if r_val >= min_rating:
            targeted_artisans.append(artisan_id)

    # 3. Dispatch (Unicast)
    if targeted_artisans:
        for artisan_id in targeted_artisans:
            msg = {
                "target_id": artisan_id,
                "data": booking_details,
            }
            # Publish to the Bridge
            redis_2.publish("socket_server_dispatch", json.dumps(msg))
    else:
        # No one met the rating criteria? Escalate immediately or after delay.
        if attempt_level < 2:
            pbq.schedule((booking_details, attempt_level + 1), delay=5)
        else:
            # inform customer that no artisan is available to handle request
            payload = {
                'payload': {
                    'message': "No handymen found at this moment, please try again later."
                },
                'recipient': booking_details['user']['user_id']
            }
            send_event('no_available_handees', payload, '/customer')


@huey.task()
def assign_artisan_to_booking(data):
    """Assign artisan to booking instance"""
    # import psycopg2
    # from psycopg2.errors import SerializationFailure
    # import psycopg2.extras
    # from dotenv import load_dotenv
    # from models import db
    _huey = HueyTemplate()
    app = _huey.get_flask_app(config_options["development"])
    db = _huey.db

    with app.app_context():
        with db.session() as sess:
            # find artisan
            artisan = (
                Artisan.query.with_session(sess).filter_by(user_id=data["uid"]).first()
            )
            artisan.jobs_assigned += 1
            booking = Booking.query.with_session(sess).get(data["booking_id"])

            booking.artisan = artisan
            booking.status = BookingStatusEnum.ARTISAN_MATCHED
            redis_4.hset(
                "booking_id_to_artisan", mapping={booking.booking_id: artisan.user_id}
            )
            redis_4.hset(
                "artisan_to_booking_id", mapping={artisan.user_id: booking.booking_id}
            )
            try:
                sess.commit()
            except Exception as e:
                logger.exception(e)
                sess.rollback()

            # TODO: find a way to avoid session required calls
            resp = BookingSchema(exclude=("artisan",), session=sess).dump(booking)

        # TODO: add expiration for stale bk requests
        redis_7.set(data["booking_id"], 1)

    # conn = psycopg2.connect(
    #     'postgresql://handees_admin:5JynGFGk0d3Zaeb2fEi7gQ@handees-db-cluster-5872.jxf.gcp-europe-west3.cockroachlabs.cloud:26257/defaultdb?sslmode=verify-full',
    #     application_name="$ docs_simplecrud_psycopg2",
    #     cursor_factory=RealDictCursor,
    #     **{
    #         "sslmode": "verify-full",
    #         "sslrootcert": "/home/handeesofficial/.postgresql/root.crt"
    #     }
    # )
    # with conn.cursor() as cur:
    #     cur.execute(
    #         "select * from user"
    #     )


@huey.task()
def update_booking_status(data):
    """updates status of booking"""
    _huey = HueyTemplate()
    app = _huey.get_flask_app(config_options["development"])
    db = _huey.db

    with app.app_context():
        # find booking
        bk = Booking.query.with_session(db.session()).get(data["booking_id"])

        # update status to artisan_arrived state
        bk.update_status(data["status"])

        try:
            db.session.commit()
        except Exception as e:
            logger.exception(e)
            db.session.rollback()
        finally:
            db.session.close()


@huey.task()
def confirm_job_details(data):
    """called when a job is started"""
    from tasks.events import send_event
    from core.api.bookings import messages
    from uuid import uuid4

    _huey = HueyTemplate()
    app = _huey.get_flask_app(config_options["development"])
    db = _huey.db

    with app.app_context():
        # find booking
        bk: Booking = Booking.query.with_session(db.session()).get(data["booking_id"])
        is_contract: bool = data["is_contract"]
        settlement: dict = data["settlement"]

        if bk.details_confirmed:
            payload = {
                "payload": {"msg": messages.BOOKING_DETAILS_ALREADY_CONFIRMED},
                "recipient": redis_4.hget("booking_id_uid", data["booking_id"]),
            }
            send_event("job_details_already_confirmed", payload, "/customer")
            return

        if is_contract:
            # set contract
            if not bk.booking_contract:
                bkc = BookingContract()
                bk.booking_contract = bkc
            else:
                raise BookingHasContract(
                    f"This booking {bk} already has a booking-contract associated with it"
                )
            db.session.add(bkc)

        # associate payment with booking
        _payment = Payment()
        _payment.payment_id = uuid4().hex
        if settlement["type"] == "NEGOTIATION":
            _payment.total_amount = settlement["amount"]

        # set booking settlement type
        bk.settlement_type = SettlementEnum[settlement["type"]]
        db.session.add(_payment)

        # assign payment to booking
        bk.payment = _payment

        # confirm bk details
        bk.details_confirmed = True

        try:
            db.session.commit()
        except Exception as e:
            logger.exception(e)
            db.session.rollback()
        finally:
            db.session.close()
        payload = {
            "payload": {"msg": messages.BOOKING_DETAILS_CONFIRMED},
            "recipient": redis_4.hget("booking_id_to_artisan", data["booking_id"]),
        }
        send_event("job_details_confirmed", payload, "/artisan")


@huey.task()
def job_end(data):
    """sets the start time of booking"""
    from models.bookings import SettlementEnum, BookingPaymentMethod
    from models.payments import CardAuth
    from models.user_models import User
    from tasks import send_event, initiate_charge
    from core.api.bookings.events.utils import gen_response
    from core.api.bookings import messages

    _huey = HueyTemplate()
    app = _huey.get_flask_app(config_options["development"])
    db = _huey.db
    customer_rid = redis_4.hget("booking_id_to_uid", data["booking_id"])
    artisan_id = redis_4.hget("booking_id_to_artisan", data["booking_id"])

    with app.app_context():
        # find booking
        bk: Booking = Booking.query.with_session(db.session()).get(data["booking_id"])
        user: User = db.session.query(User).get(bk.customer_id)
        artisan: Artisan = db.session.query(Artisan).get(bk.artisan_id)
        artisan.update_completed_job_count()

        if bk.status == BookingStatusEnum.IN_PROGRESS:
            bk.update_end_time()

            # update booking status
            bk.update_status(BookingStatusEnum.COMPLETED)

            send_event(
                "job_completed",
                gen_response(customer_rid, data={"msg": messages.JOB_COMPLETED}),
                "/customer",
            )

            # calculate amount to be paid if
            # settlement type is "hrly"
            if bk.settlement_type == SettlementEnum.HOURLY_RATE:
                pay = bk.fetch_hourly_pay()
                bk.payment.total_amount = pay
            else:
                pay = bk.payment.total_amount

            # convert to naira from kobo
            pay *= 100.0

            # inform artisan of total
            send_event(
                "settlement_total",
                {"recipient": data["uid"], "payload": {"total_amount": pay}},
                namespace="/artisan",
            )

            # check if card payment and initiate a charge on card
            if bk.payment_method == BookingPaymentMethod.CARD:
                # TODO: perhaps verify that user has card before trying this
                charge_obj = {
                    "charge_info": {
                        "authorization_code": db.session.query(CardAuth)
                        .filter_by(user_id=bk.customer_id)  # noqa: E501
                        .first()
                        .authorization_code,
                        "email": user.email,
                        "amount": pay,
                        "callback_url": app.config["SERVER_NAME"]
                        + "/api/payments/charge_callback",
                    },
                    "customer_info": {"user_rid": customer_rid},
                    "artisan_id": artisan_id,
                }
                initiate_charge(charge_obj)

            try:
                db.session.commit()
            except Exception as e:
                logger.exception(e)
                db.session.rollback()
            finally:
                db.session.close()
        else:
            send_event(
                "error",
                {
                    "recipient": data["uid"],
                    "payload": {
                        "data": "Invalid Transaction Attempted: Can't move "
                        f"job from status {bk.status} "
                        f"to {BookingStatusEnum.IN_PROGRESS}"
                    },
                },
                namespace="/artisan",
            )
            logger.error(
                "Invalid Transaction Attempted: Can't move job from status "
                f"{bk.status} to {BookingStatusEnum.IN_PROGRESS}"
            )
