# flake8: noqa E402
from flask import Blueprint


api = Blueprint('api', __name__, url_prefix='/api')

from .bookings import bookings
from .payments import payments
from .security import security
from .user import user
from .ratings import ratings


api.register_blueprint(bookings)
api.register_blueprint(payments)
api.register_blueprint(security)
api.register_blueprint(user)
api.register_blueprint(ratings)
