from flask import Blueprint

customer = Blueprint("customer", __name__, url_prefix="/customer")

from . import views

