from .push_booking_to_queue import huey
from models.payments import Payment
from config import config_options
from extensions import HueyTemplate


@huey.task()
def create_transaction(data):
    from models import db
    app = HueyTemplate.get_flask_app(config_options['staging'])

    with app.app_context():
        pass
