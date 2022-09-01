from extensions import HueyTemplate, redis_
from .push_booking_to_queue import huey
from models.user_models import Artisan
from models.bookings import Booking
from schemas.bookings_schema import BookingSchema
from config import config_options
import logging

logging.basicConfig(level=logging.DEBUG)


# TODO: subclass decorator to include app context

@huey.task()
def assign_artisan_to_booking(data):
    """Assign artisan to booking instance"""
    from models import db
    app = HueyTemplate.get_flask_app(config_options['staging'])

    with app.app_context():
        # find artisan
        artisan = Artisan.query.get(data['artisan_id'])
        booking = Booking.query.get(data['booking_id'])

        booking.artisan = artisan
        db.session.commit()

        resp = BookingSchema().dump(booking)
        redis_.set(
            data['booking_id'],
            str(resp)
        )


@huey.task()
def update_booking_status(data):
    """ updates status of booking """
    from models import db
    app = HueyTemplate.get_flask_app(config_options['staging'])

    with app.app_context():
        # find booking
        bk = Booking.query.get(data['booking_id'])

        bk.update_status(data['status_code'])

        db.session.commit()

        resp = BookingSchema().dump(bk)
        redis_.set(
            data['booking_id'],
            str(resp)
        )


@huey.task()
def job_start(data):
    """ called when a job is started """
    from models import db

    app = HueyTemplate.get_flask_app(config_options['staging'])

    with app.app_context():
        # find booking
        bk = Booking.query.get(data['booking_id'])

        # update start time
        bk.update_start_time()

        # update booking status
        bk.update_status(8)

        db.session.commit()


@huey.task()
def job_end(data):
    """ sets the start time of booking """
    from models import db
    from models.bookings import SettlementEnum

    app = HueyTemplate.get_flask_app(config_options['staging'])

    with app.app_context():
        # find booking
        bk = Booking.query.get(data['booking_id'])

        bk.update_end_time()

        # update booking status
        bk.update_status(4)

        # calculate amount to be paid if 
        # settlement type is "hrly"
        

        db.session.commit()
