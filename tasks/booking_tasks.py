from extensions import (
    HueyTemplate,
    redis_,
    redis_2,
    redis_4
)
from .events import send_event
from core.exc import BookingHasContract
from config import BaseConfig
from models.user_models import Artisan
from models.bookings import (
    Booking,
    BookingContract,
    BookingStatusEnum,
    SettlementEnum
)
from tasks.exc import InvalidBookingTransaction
from models.payments import Payment
from schemas.bookings_schema import BookingSchema
from config import config_options


import logging


logging.basicConfig(level=logging.DEBUG)

# huey instance
huey = HueyTemplate(config=BaseConfig.HUEY_CONFIG).huey
logging.getLogger('huey').setLevel(logging.DEBUG)

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

    redis_2.set(booking_details['booking_id'], str(booking_details))

    # broadcast message to artisans using a redis pub/sub channel
    # the channel is unique to each artisan and its id is synonymous
    # to the artisan's geohash
    redis_2.publish(g_hash[0][:7], str(booking_details))


@huey.task()
def assign_artisan_to_booking(data):
    """Assign artisan to booking instance"""
    from models import db
    app = HueyTemplate.get_flask_app(config_options['development'])

    with app.app_context():
        # find artisan
        artisan = Artisan.query.get(data['artisan_id'])
        booking = Booking.query.get(data['booking_id'])

        booking.artisan = artisan
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
        finally:
            resp = BookingSchema().dump(booking)
            db.session.close()

        redis_.set(
            data['booking_id'],
            str(resp)
        )


@huey.task()
def update_booking_status(data):
    """ updates status of booking """
    from models import db
    app = HueyTemplate.get_flask_app(config_options['development'])

    with app.app_context():
        # find booking
        bk = Booking.query.get(data['booking_id'])

        bk.update_status(data['status_code'])

        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
        finally:
            db.session.close()

        resp = BookingSchema().dump(bk)
        redis_.set(
            data['booking_id'],
            str(resp)
        )


@huey.task()
def confirm_job_details(data):
    """ called when a job is started """
    from models import db

    app = HueyTemplate.get_flask_app(config_options['development'])

    with app.app_context():
        # find booking
        bk: Booking = Booking.query.get(data['booking_id'])
        is_contract: bool = data['is_contract']
        settlement: dict = data['settlment']

        if is_contract:

            # set contract
            if not bk.booking_contract:
                bkc = BookingContract()
                bk.booking_contract = bkc

                bkc.update_start_time()
            else:
                raise BookingHasContract(
                    f"This booking {bk} already has a booking-contract associated with it"
                )

        # associate payment with booking
        _payment = Payment()
        if settlement['type'] == 'NEGOTIATION':
            _payment.total_amount = settlement['amount']

        # set booking settlement type
        bk.settlement_type = SettlementEnum[settlement['type']]

        # assign payment to booking
        bk.payment = _payment

        try:
            db.session.add(bkc)
            db.session.add(_payment)
            db.session.commit()
        except Exception:
            db.session.rollback()
        finally:
            db.session.close()


@huey.task()
def job_end(data):
    """ sets the start time of booking """
    from models import db
    from models.bookings import SettlementEnum

    app = HueyTemplate.get_flask_app(config_options['development'])

    with app.app_context():
        # find booking
        bk: Booking = Booking.query.get(data['booking_id'])

        if bk.status == BookingStatusEnum('8'):
            bk.update_end_time()

            # update booking status
            bk.update_status('4')

            # calculate amount to be paid if
            # settlement type is "hrly"
            user_rid = redis_4.hget(
                'user_to_sid',
                Artisan.query.get(data['artisan_id']).user_id
            )
            if bk.settlement_type == SettlementEnum('1'):
                pay = bk.fetch_hourly_pay()
                bk.payment.total_amount = pay
            else:
                pay = bk.payment.total_amount
            # inform artisan of total
            send_event(
                'settlement_total',
                {
                    'recipient': user_rid,
                    'payload': pay
                },
                namespace='/artisan'
            )
            try:
                db.session.commit()
            except Exception:
                db.session.rollback()
            finally:
                db.session.close()
        else:
            raise InvalidBookingTransaction(
                "Invalid Transaction Attempted: Can't move job from status "
                f"{bk.status} to {BookingStatusEnum('8')}"
            )
