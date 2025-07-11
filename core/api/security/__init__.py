from flask import Blueprint

security = Blueprint("security", __name__, url_prefix="/security")

from . import views

