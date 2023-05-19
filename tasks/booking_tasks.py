from extensions import (
    HueyTemplate,
    redis_,
    redis_2,
    redis_4
)
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

import functools
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
def job_start(data):
    """ called when a job is started """
    from models import db

    app = HueyTemplate.get_flask_app(config_options['development'])

    with app.app_context():
        # find booking
        bk: Booking = Booking.query.get(data['booking_id'])
        is_contract: bool = data['is_contract']
        settlement: dict = data['settlment']

        if bk.status == BookingStatusEnum('8'):
            raise InvalidBookingTransaction("Job started already")

        if is_contract:
            # update start time
            bk.update_start_time()

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

        # update booking status
        bk.update_status('8')

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
            if bk.settlement_type == SettlementEnum('1'):
                pay = bk.fetch_hourly_pay()
                user_id = Artisan.query.get(data['artisan_id']).user_id
                bk.payment.total_amount = pay
                # inform artisan of total
                send_event(
                    'settlement_total',
                    {
                        'recipient': user_id,
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


def exp_backoff_task(retries, retry_backoff):
    def deco(fn):
        @functools.wraps(fn)
        def inner(*args, **kwargs):
            # We will register this task with `context=True`, which causes
            # Huey to pass the task instance as a keyword argument to the
            # decorated task function. This enables us to modify its retry
            # delay, multiplying it by our backoff factor, in the event of
            # an exception.
            task = kwargs.pop('task')
            try:
                return fn(*args, **kwargs)
            except Exception as exc:
                task.retry_delay *= retry_backoff
                raise exc

        # Register our wrapped task (inner()), which handles delegating to
        # our function, and in the event of an unhandled exception,
        # increases the retry delay by the given factor.
        return huey.task(retries=retries, retry_delay=2, context=True)(inner)
    return deco


@exp_backoff_task(retries=3, retry_backoff=1.15)
def send_event(event, data, namespace):
    from flask_socketio import SocketIO
    from core.exc import ClientNotConnected

    # check if receiver is connected
    user_sid = redis_4.hget("user_to_sid", data['recipient'])
    if not redis_4.exists(user_sid):
        raise ClientNotConnected("Client no longer connected")

    sock = SocketIO(
        cors_allowed_origins=[
            'http://127.0.0.1:5020', 'http://127.0.0.1:5500',
            'https://www.piesocket.com'
        ],
        message_queue="redis://redis:6378/2",
        async_mode='eventlet',
        logger=True,
        engineio_logger=True
    )
    resp = sock.emit(
        event,
        data['payload'],
        to=user_sid,
        namespace=namespace
    )
    print(resp)
