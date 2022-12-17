# flake8: noqa

from flask import Blueprint

user = Blueprint("user", __name__, url_prefix="/user")

from .artisan import artisan
from . import views

# register sub-blueprints
user.register_blueprint(artisan)
