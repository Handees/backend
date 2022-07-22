# flake8: noqa

from flask import Blueprint

bookings = Blueprint(
    "bookings", __name__, template_folder='templates'
)

from . import views, events
