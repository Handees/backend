# flake8: noqa
import eventlet
eventlet.monkey_patch() # https://stackoverflow.com/questions/63026435/maximum-recursion-depth-exceeded-on-sslcontext-eventlet-flask-flask-socketio

from json import load
from core import create_app, socketio, db
from dotenv import load_dotenv
from models import *
from utils import (
    get_class_by_tablename,
    load_env,
    fetch_instance_tag
)
from google.cloud import secretmanager
from google import auth
import click
import os
import pipes
import sys
import base64
import firebase_admin


load_dotenv()


app = create_app(os.getenv('APP_ENV') or 'default')
cred = firebase_admin.credentials.Certificate(app.config['F_KEY_PATH'])
firebase_admin.initialize_app(cred)

# test config
COV = None

if app.config['FLASK_COVERAGE']:
    import coverage
    COV = coverage.Coverage(
        branch=True,
        source=[
            'core/',
            'models/',
            'schemas/'
        ]
    )
    # COV.
    COV.start()


# flask shell
@app.shell_context_processor
def make_shell_context():
    return dict(
        app=app,
        role=Role,
        user=User,
        artisan=Artisan,
        bk_cat=BookingCategory,
        db=db
    )


# flask cli commands
@app.cli.command()
def create_categories():
    """creates job categories in db"""
    print("Creating categories::", end='\n')
    BookingCategory.create_categories()
    print("Done!")


# purge table
@app.cli.command()
@click.option(
    '--table_name',
    help="specify name of table to be deleted"
)
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
@click.option(
    '--coverage/--no-coverage', default=False,
    help='Run tests under coverage'
)
def test(coverage):
    """ Run the unit tests """
    # if not coverage and not app.config['FLASK_COVERAGE']:
    #     app.config['FLASK_COVERAGE'] = True
    #     # os.execvp(sys.executable, [sys.executable] + sys.argv)
    #     return
    import unittest
    test = unittest.TestLoader().discover('tests')
    unittest.TextTestRunner(verbosity=2).run(test)
    if COV and coverage:
        COV.stop()
        COV.save()
        print("Coverage Summary: ")
        COV.report()
        basedir = os.path.abspath(os.path.dirname(__file__))
        print(basedir)
        covdir = os.path.join(basedir, 'tmp/coverage')
        COV.html_report(directory=covdir)
        print('HTML version: file://%s/index.html' % covdir)
        COV.erase()


@app.cli.command()
def load_config_variables():
    """fetches secrets from GCP secret manager and loads them into .env"""
    def gen_pairs(obj):
        val = base64.b64decode(obj['payload']['data']).decode('utf-8')
        yield f"{pipes.quote(obj['name'].split('/')[-3])}={pipes.quote(val)}"

    access_token = None
    keys = load_env(gen_pairs)

    if keys:
        try:
            with open('.env', 'w') as file:
                for kv in keys:
                    file.write(kv)
                    file.write("\n")
            print("Written config secrets to .env")
        except Exception as e:
            print("Something went wrong while writing to .env")
            raise e
    else:
        raise Exception("Something went wrong while trying to fetch secrets")
if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
