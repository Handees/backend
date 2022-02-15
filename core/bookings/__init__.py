from flask import Blueprint

bookings = Blueprint("bookings", __name__, url_prefix="/bookings")

from . import views
