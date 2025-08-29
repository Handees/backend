import os

from extensions import (
    HueyTemplate,
    redis_,
    redis_2,
    redis_4
)
from core.exc import BookingHasContract
# from core.extensions import db
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
from utils import setLogger
from config import config_options


import uuid
import logging
from loguru import logger
from huey import Huey
from flask import url_for


logging.basicConfig(level=logging.DEBUG)

# huey instance
huey: Huey = HueyTemplate(config=BaseConfig.HUEY_CONFIG).huey
logging.getLogger('huey').setLevel(logging.DEBUG)

setLogger()

# TODO: subclass decorator to include app context


@huey.task()
@huey.lock_task('lock_broadcast_task')
def pbq(booking_details):
    # find nearest artisans to customer
    lat, lon = booking_details['lat'], booking_details['lon']
    redis_2.geoadd(
        name="customer_pos",
        values=(lon, lat, booking_details['user']['user_id'])
    )
    g_hash = redis_2.geohash(
        'customer_pos',
        booking_details['user']['user_id']
    )

    redis_.set(booking_details['booking_id'], str(booking_details))

    # broadcast message to artisans using a redis pub/sub channel
    # the channel is unique to each artisan and its id is synonymous
    # to the artisan's geohash
    print(g_hash[0][:5], "customer loc ghash")

    # TODO: filter neighbouring points here to address boundary problem
    #  and also properly cast to desired radius.

    redis_2.publish(g_hash[0][:5], str(booking_details))


@huey.task()
def assign_artisan_to_booking(data):
    """Assign artisan to booking instance"""
    # import psycopg2
    # from psycopg2.errors import SerializationFailure
    # import psycopg2.extras
    # from dotenv import load_dotenv
    # from models import db
    _huey = HueyTemplate()
    app = _huey.get_flask_app(config_options['development'])
    db = _huey.db

    with app.app_context():
        with db.session() as sess:
            # find artisan
            artisan = Artisan.query.with_session(sess).filter_by(
                user_id=data['uid']
            ).first()
            booking = Booking.query.with_session(sess).get(
                data['booking_id']
            )

            booking.artisan = artisan
            redis_4.hset(
                'booking_id_to_artisan',
                mapping={booking.booking_id: artisan.user_id}
            )
            redis_4.hset(
                'artisan_to_booking_id',
                mapping={artisan.user_id: booking.booking_id}
            )
            try:
                sess.commit()
            except Exception as e:
                logger.exception(e)
                sess.rollback()

            # TODO: find a way to avoid session required calls
            resp = BookingSchema(
                exclude=('artisan',),
                session=sess
            ).dump(booking)

    # conn = psycopg2.connect(
    #     'postgresql://handees_admin:5JynGFGk0d3Zaeb2fEi7gQ@handees-db-cluster-5872.jxf.gcp-europe-west3.cockroachlabs.cloud:26257/defaultdb?sslmode=verify-full',
    #     application_name="$ docs_simplecrud_psycopg2",
    #     cursor_factory=RealDictCursor,
    #     **{
    #         "sslmode": "verify-full",
    #         "sslrootcert": "/home/handeesofficial/.postgresql/root.crt"
    #     }
    # )
    # with conn.cursor() as cur:
    #     cur.execute(
    #         "select * from user"
    #     )


@huey.task()
def update_booking_status(data):
    """ updates status of booking """
    _huey = HueyTemplate()
    app = _huey.get_flask_app(config_options['development'])
    db = _huey.db

    with app.app_context():
        # find booking
        bk = Booking.query.with_session(
            db.session()
        ).get(data['booking_id'])

        # update status to artisan_arrived state
        bk.update_status('1')

        try:
            db.session.commit()
            resp = BookingSchema().dump(bk)
        except Exception as e:
            logger.exception(e)
            db.session.rollback()
        finally:
            db.session.close()

        redis_.set(
            data['booking_id'],
            str(resp)
        )


@huey.task()
def confirm_job_details(data):
    """ called when a job is started """
    from tasks.events import send_event
    from core.api.bookings import messages
    from uuid import uuid4

    _huey = HueyTemplate()
    app = _huey.get_flask_app(config_options['development'])
    db = _huey.db

    with app.app_context():
        # find booking
        bk: Booking = Booking.query.with_session(
            db.session()
        ).get(data['booking_id'])
        is_contract: bool = data['is_contract']
        settlement: dict = data['settlement']

        if bk.details_confirmed:
            payload = {
                'payload': {'msg': messages.BOOKING_DETAILS_ALREADY_CONFIRMED},
                'recipient': redis_4.hget(
                    'booking_id_uid',
                    data['booking_id']
                )
            }
            send_event(
                'job_details_already_confirmed',
                payload,
                '/customer'
            )
            return

        if is_contract:
            # set contract
            if not bk.booking_contract:
                bkc = BookingContract()
                bk.booking_contract = bkc
            else:
                raise BookingHasContract(
                    f"This booking {bk} already has a booking-contract associated with it"
                )
            db.session.add(bkc)

        # associate payment with booking
        _payment = Payment()
        _payment.payment_id = uuid4().hex
        if settlement['type'] == 'NEGOTIATION':
            _payment.total_amount = settlement['amount']

        # set booking settlement type
        bk.settlement_type = SettlementEnum[settlement['type']]
        db.session.add(_payment)

        # assign payment to booking
        bk.payment = _payment

        # confirm bk details
        bk.details_confirmed = True

        try:
            db.session.commit()
        except Exception as e:
            logger.exception(e)
            db.session.rollback()
        finally:
            db.session.close()
        payload = {
            'payload': {'msg': messages.BOOKING_DETAILS_CONFIRMED},
            'recipient': redis_4.hget(
                'booking_id_to_artisan',
                data['booking_id']
            )
        }
        send_event(
            'job_details_confirmed',
            payload,
            '/artisan'
        )


@huey.task()
def job_end(data):
    """ sets the start time of booking """
    from models.bookings import (
        SettlementEnum,
        BookingPaymentMethod
    )
    from models.payments import CardAuth
    from models.user_models import User
    from tasks import (
        send_event,
        initiate_charge
    )
    from core.api.bookings.events.utils import gen_response
    from core.api.bookings import messages

    _huey = HueyTemplate()
    app = _huey.get_flask_app(config_options['development'])
    db = _huey.db
    customer_rid = redis_4.hget(
        'booking_id_to_uid',
        data['booking_id']
    )

    with app.app_context():
        # find booking
        bk: Booking = Booking.query.with_session(
            db.session()
        ).get(data['booking_id'])
        user: User = db.session.query(User).get(bk.customer_id)

        if bk.status == BookingStatusEnum.IN_PROGRESS:
            bk.update_end_time()

            # update booking status
            bk.update_status(BookingStatusEnum.COMPLETED)

            send_event(
                'job_completed',
                gen_response(
                    customer_rid,
                    data={
                        'msg': messages.JOB_COMPLETED
                    }
                ),
                '/customer'
            )

            # calculate amount to be paid if
            # settlement type is "hrly"
            if bk.settlement_type == SettlementEnum.HOURLY_RATE:
                pay = bk.fetch_hourly_pay()
                bk.payment.total_amount = pay
            else:
                pay = bk.payment.total_amount

            # convert to naira from kobo
            pay *= 100.0

            # inform artisan of total
            send_event(
                'settlement_total',
                {
                    'recipient': data['uid'],
                    'payload': {'total_amount': pay}
                },
                namespace='/artisan'
            )

            # check if card payment and initiate a charge on card
            if bk.payment_method == BookingPaymentMethod.CARD:
                # TODO: perhaps verify that user has card before trying this
                charge_obj = {
                    'charge_info': {
                        'authorization_code': db.session.query(CardAuth).filter_by(  # noqa: E501
                            user_id=bk.customer_id
                        ).first().authorization_code,
                        'email': user.email,
                        'amount': pay,
                        'callback_url': app.config['SERVER_NAME'] \
                            + '/api/payments/charge_callback'
                    },
                    'customer_info': {
                        'user_rid': customer_rid
                    }
                }
                initiate_charge(charge_obj)

            try:
                db.session.commit()
            except Exception as e:
                logger.exception(e)
                db.session.rollback()
            finally:
                db.session.close()
        else:
            send_event(
                'error',
                {
                    'recipient': data['uid'],
                    'payload': {
                        'data': "Invalid Transaction Attempted: Can't move "
                        f"job from status {bk.status} "
                        f"to {BookingStatusEnum.IN_PROGRESS}"
                    }
                },
                namespace='/artisan'
            )
            logger.error(
                "Invalid Transaction Attempted: Can't move job from status "
                f"{bk.status} to {BookingStatusEnum.IN_PROGRESS}"
            )
