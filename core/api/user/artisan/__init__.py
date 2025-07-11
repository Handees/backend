from flask import Blueprint

artisan = Blueprint("artisan", __name__, url_prefix="/artisan")

from . import views

