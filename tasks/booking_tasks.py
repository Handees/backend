from extensions import redis_, HueyTemplate
from .push_booking_to_queue import huey
from models.user_models import Artisan
from models.bookings import Booking
from schemas.bookings_schema import BookingSchema
from config import config_options
import logging

logging.basicConfig(level=logging.DEBUG)


@huey.task()
def assign_artisan_to_booking(data):
    """Assign artisan to booking instance"""
    app, db = HueyTemplate.get_flask_app(config_options['staging'])
    print(db)
    print(app, app.config)
    with app.app_context():
        db.session.begin()
        # find artisan
        artisan = Artisan.query.get(data['artisan_id'])
        booking = Booking.query.get(data['booking_id'])

        booking.artisan = artisan
        db.session.commit()

        resp = BookingSchema().dump(booking)
        print(resp)
        redis_.set(data['booking_id'], str(resp))
