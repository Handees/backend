
from flask import Blueprint

payments = Blueprint("payments", __name__, url_prefix="/payments")

from . import views
