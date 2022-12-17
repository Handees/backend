from flask import Blueprint

ratings = Blueprint("ratings", __name__, url_prefix="/ratings")

from . import views

