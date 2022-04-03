# flake8: noqa

from json import load
from core import create_app
from dotenv import load_dotenv
from models.user_models import *
from models.base import *
from models.documents import *
from models.address import *
import os

load_dotenv()

app = create_app(os.getenv('FLASK_CONFIG') or 'default')

@app.shell_context_processor
def make_shell_context():
    return dict(app=app, role=Role)
