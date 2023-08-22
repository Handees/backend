from core import (
    socketio,
    db
)
from .utils import (
    error_response,
    gen_response
)
from core.api.auth.auth_helper import (
    auth_param_required,
    valid_auth_required
)
from tasks.booking_tasks import update_booking_status
from tasks.events import send_event
from extensions import (
    redis_2,
    redis_4
)
from utils import (
    LOG_FORMAT, _level
)
from core.exc import (
    DataValidationError,
    InvalidBookingTransaction
)
from core.api.auth.auth_helper import verify_token
from core.api.bookings.events.utils import parse_event_data
from schemas.bookings_schema import BookingStartSchema
from schemas.artisan import ArtisanSchema
from models import (
    Artisan,
    Booking
)
from models.bookings import BookingStatusEnum
from .. import messages

from flask import (
    request,
    session
)
from flask_socketio import (
    emit,
    join_room,
    ConnectionRefusedError
)
from loguru import logger
import sys


# configure local logger
logger.remove()

logger.add(
    sys.stderr,
    format=LOG_FORMAT,
    colorize=True,
    level=_level
)


@socketio.on('connect', namespace='/chat')
def enter_chat_namespace(data):
    emit('msg', 'welcome to chat')


@socketio.on('join_chat', namespace='/chat')
def enter_chat_room(data):
    room = data['booking_id']
    join_room(room)


@socketio.on_error('/artisan')
def default_error_handler(e):
    logger.exception(e)
    socketio.emit(str(e), to=request.sid, )


@socketio.on('connect', namespace='/artisan')
@auth_param_required
def on_connect(auth):
    uid = verify_token(auth['access_token'])
    if not uid:
        raise ConnectionRefusedError
    session['uid'] = uid
    emit('msg', 'welcome!')
    redis_4.set(request.sid, 1)
    redis_4.hset(
        "user_to_sid",
        mapping={uid: request.sid}
    )
    redis_4.hset(
        "sid_to_user",
        mapping={request.sid: uid}
    )
    logger.debug('new artisan {} client connection!'.format(request.sid))


@socketio.on('disconnect', namespace='/artisan')
def on_disconnect():
    if redis_4.exists(request.sid):
        redis_4.delete(request.sid)
    sid_all = redis_4.hgetall("sid_to_user")
    uid_all = redis_4.hgetall("user_to_sid")
    if request.sid in sid_all:
        del uid_all[sid_all[request.sid]]
        del sid_all[request.sid]
    if sid_all:
        redis_4.hset("sid_to_user", mapping=sid_all)
    if uid_all:
        redis_4.hset("user_to_sid", mapping=uid_all)


@socketio.on('location_update', namespace='/artisan')
@parse_event_data
@valid_auth_required
def update_location(uid, data):
    # TODO: add data validation
    # update artisan location on redis
    room = uid
    join_room(room)

    psub = redis_2.pubsub()
    psub.unsubscribe('*')

    redis_2.geoadd(
        name=data['job_category'],
        values=(data['lon'], data['lat'], uid)
    )
    g_hash = redis_2.geohash(
        data['job_category'],
        uid
    )
    logger.debug(g_hash)
    # reduce geohash length to 6 charz
    # subscribe useto a topic named after this
    # truncated geohash

    def handle_updates(msg):
        socketio.emit('new_offer', eval(msg['data']), to=room, namespace='/artisan')

    psub.subscribe(**{g_hash[0][:7]: handle_updates})

    psub.run_in_thread(sleep_time=.01)


@socketio.on('accept_offer', namespace='/artisan')
@parse_event_data
@valid_auth_required
def get_updates(uid, data):
    """ triggered when artisan accepts offer """
    from tasks.booking_tasks import assign_artisan_to_booking

    room = data['booking_id']
    data['uid'] = uid
    if redis_2.exists(room):
        # remove from queue
        redis_2.delete(room)

        # assign artisan to booking
        try:
            assign_artisan_to_booking(data)
        except Exception as e:
            logger.exception(e)
            send_event(
                'error',
                error_response(messages.INTERNAL_SERVER_ERROR, uid),
                '/artisan'
            )
            return

        # send updates to user
        artisan = ArtisanSchema().dump(Artisan.get_by_user_id(uid))
        data['artisan'] = artisan
        del data['uid']
        payload = {
            'payload': data,
            'recipient': redis_4.hget(
                'booking_id_to_uid',
                data['booking_id']
            )
        }
        try:
            send_event('booking_offer_accepted', payload, '/customer')
            send_event(
                'offer_matched',
                {
                    'payload': data,
                    'recipient': redis_4.hget(
                        'booking_id_to_artisan',
                        data['booking_id']
                    )
                },
                '/artisan'
            )
        except Exception as e:
            logger.error(e)
            emit('offer_matched', data)
    else:
        payload = {
            'payload': {'msg': messages.BOOKING_CANCELLED, 'data': {}},
            'recipient': uid
        }
        send_event('offer_closed', payload, '/artisan')


@socketio.on('cancel_offer', namespace='/artisan')
@parse_event_data
@valid_auth_required
def cancel_offer_artisan(uid, data):
    """ triggered when artisan cancels offer """
    from schemas.bookings_schema import CancelBookingSchema

    schema = CancelBookingSchema()

    try:
        data = schema.load(data)
    except Exception as e:
        raise DataValidationError(messages.SCHEMA_ERROR, errors=e)

    room = data['booking_id']

    # update status of booking
    try:
        update_booking_status(data)
    except Exception as e:
        logger.exception(e)
        send_event(
            'error',
            error_response(messages.INTERNAL_SERVER_ERROR, uid),
            '/artisan'
        )

    # remove from queue once canceled
    redis_2.delete(room)

    socketio.emit(
        'offer_cancelled',
        messages.dynamic_msg(messages.BOOKING_CANCELLED, "artisan"),
        to=room
    )


@socketio.on('arrived_location', namespace='/artisan')
@parse_event_data
@valid_auth_required
def handle_location_arrival(uid, data):
    """ triggered when artisan arrives at location """

    # update booking status
    try:
        update_booking_status(data)
    except Exception as e:
        logger.exception(e)
        send_event(
            'error',
            error_response(messages.INTERNAL_SERVER_ERROR, uid),
            '/artisan'
        )

    payload = {
        'payload': messages.ARTISAN_ARRIVES,
        'recipient': redis_4.hget(
            'booking_id_to_uid',
            data['booking_id']
        )
    }
    send_event('artisan_arrived', payload, '/customer')


@socketio.on('start_job', namespace='/artisan')
@parse_event_data
@valid_auth_required
def handle_job_begin(uid, data):
    """ triggered when artisan begins a job """
    artisan = Artisan.get_by_user_id(uid)
    bk = Booking.query.get(data['booking_id'])

    # check if customer has confirmed job
    if not bk.details_confirmed:
        logger.error(InvalidBookingTransaction(
            f"{messages.BOOKING_NOT_CONFIRMED}"
        ))
        send_event(
            'error',
            error_response(messages.BOOKING_NOT_CONFIRMED, uid),
            '/artisan'
        )
        return

    # initiate job
    if bk.artisan.artisan_id == artisan.artisan_id:
        try:
            if not bk.status == BookingStatusEnum('8'):
                bk.update_status('8')
                try:
                    db.session.commit()
                    payload = {
                        'payload': messages.JOB_STARTED,
                        'recipient': redis_4.hget(
                            'booking_id_to_uid',
                            data['booking_id']
                        )
                    }
                    send_event(
                        'job_started',
                        payload,
                        '/customer'
                    )
                except Exception as e:
                    logger.exception(e)
                    db.session.rollback()
                    send_event(
                        'error',
                        error_response(messages.INTERNAL_SERVER_ERROR, uid),
                        '/artisan'
                    )
                    raise e
                finally:
                    db.session.close()
        except Exception as e:
            logger.exception(e)
            send_event(
                'error',
                error_response(messages.INTERNAL_SERVER_ERROR, uid),
                '/artisan'
            )
            return
    else:
        logger.error(InvalidBookingTransaction(
            f"Artisan with id {artisan.artisan_id} has not been assigned this order"
        ))
        send_event(
            'error',
            error_response(f"Artisan with id {artisan.artisan_id} has not been assigned this order", uid),
            '/artisan'
        )


@socketio.on('job_completed', namespace='/artisan')
@parse_event_data
@valid_auth_required
def handle_job_end(uid, data):
    """ triggered when artisan ends a job """
    from tasks.booking_tasks import job_end

    try:
        data['uid'] = uid
        job_end(data)
        send_event(
            'job_completed',
            gen_response(
                data={
                    'msg': messages.JOB_COMPLETED
                }
            ),
            '/customer'
        )
    except Exception as e:
        logger.exception(e)
        send_event(
            'error',
            error_response(messages.INTERNAL_SERVER_ERROR, uid),
            '/artisan'
        )
        return


@socketio.on('request_customer_approval', namespace='/artisan')
@parse_event_data
@valid_auth_required
def customer_approval(uid, data):
    """ triggered when artisan specifies initial details of the booking """
    try:
        schema = BookingStartSchema()
        data = schema.load(data)
    except Exception as e:
        logger.error(messages.SCHEMA_ERROR)
        logger.error(e)
        send_event(
            'error',
            error_response(e.messages, uid),
            '/artisan'
        )
        return

    # inform customer
    payload = {
        'payload': data,
        'recipient': redis_4.hget(
            'booking_id_to_uid',
            data['booking_id']
        )
    }
    send_event('approve_booking_details', payload, '/customer')


@socketio.on('msg', namespace='/chat')
@parse_event_data
@valid_auth_required
def send_chat_msg(uid, data):
    """sends message to chat room"""
    msg = data['msg']
    room = data['booking_id']
    socketio.emit('msg', msg, to=room, namespace='/chat')
