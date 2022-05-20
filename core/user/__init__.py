from flask import Blueprint

user = Blueprint("user", __name__, url_prefix="/user")

from .artisan import artisan
from .customer import customer
from . import views

# register sub-blueprints
user.register_blueprint(artisan)
user.register_blueprint(customer)
