# flake8: noqa
import os

import firebase_admin
from dotenv import load_dotenv

from . import second_task
from . import booking_tasks
from .payments import (
    create_transaction,
    charge_sucess,
    initiate_charge,
    initiate_refund,
    initiate_withdrawal
)
from .events import send_event

load_dotenv()

F_KEY_PATH = os.path.join(
    os.path.abspath(os.getcwd()),
    os.getenv('F_KEY')
)
cred = firebase_admin.credentials.Certificate(F_KEY_PATH)
firebase_admin.initialize_app(cred, name="firebase_admin_huey")