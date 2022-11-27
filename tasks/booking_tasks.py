from extensions import (
    HueyTemplate,
    redis_,
    redis_2
)
from core.exc import BookingHasContract
from config import BaseConfig
from models.user_models import Artisan
from models.bookings import Booking
from schemas.bookings_schema import BookingSchema
from config import config_options

import logging

logging.basicConfig(level=logging.DEBUG)

# huey instance
huey = HueyTemplate(config=BaseConfig.HUEY_CONFIG).huey

# TODO: subclass decorator to include app context


@huey.task()
def pbq(booking_details):
    # find nearest artisans to customer
    lat, lon = booking_details['lat'], booking_details['lon']
    redis_2.geoadd(
        name="customer_pos",
        values=(lon, lat, booking_details['user_id'])
    )
    g_hash = redis_2.geohash(
        'customer_pos',
        booking_details['user_id']
    )
    print(g_hash)
    print(g_hash[0][:7])

    redis_2.set(booking_details['booking_id'], str(booking_details))

    # broadcast message to artisans using a redis pub/sub channel
    # the channel is unique to each artisan and its id is synonymous
    # to the artisan's geohash
    redis_2.publish(g_hash[0][:7], str(booking_details))


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
    from core import socketio

    app = HueyTemplate.get_flask_app(config_options['staging'])

    with app.app_context():
        # find booking
        bk = Booking.query.get(data['booking_id'])

        bk.update_end_time()

        # update booking status
        bk.update_status(4)

        # calculate amount to be paid if
        # settlement type is "hrly"
        if bk.settlement_type == SettlementEnum[1]:
            pay = bk.fetch_hourly_pay()

            socketio.emit(
                'settlement_total',
                pay,
                to=data['artisan_id'],
                namespace='/artisan'
            )

        db.session.commit()


@huey.task()
def update_job_type(data):
    """ updates booking to contract type """
    from models.bookings import BookingContract
    from models import db

    app = HueyTemplate.get_flask_app(config_options['staging'])

    with app.app_context():
        bk = Booking.query.get(data['booking_id'])

        # create new booking contract
        if not bk.booking_contract:
            bkc = BookingContract()
            bk.booking_contract = bkc

            db.session.add(bkc)
            db.session.commit()
        else:
            raise BookingHasContract(
                f"This booking {bk} already has a booking-contract associated with it"
            )
