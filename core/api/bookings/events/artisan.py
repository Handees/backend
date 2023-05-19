from core import socketio
from core.api.bookings.utils import (
    auth_param_required,
    valid_auth_required
)
from tasks.booking_tasks import (
    update_booking_status,
    send_event
)
from extensions import (
    redis_2,
    redis_4
)
from core.utils import (
    LOG_FORMAT, _level
)
from core.exc import (
    DataValidationError,
    InvalidBookingTransaction
)
from core.api.auth.auth_helper import verify_token
from core.api.bookings.events.utils import parse_event_data
from schemas.bookings_schema import BookingStartSchema
from models import Artisan
from .. import messages

from flask import (
    request,
    session
)
from flask_socketio import (
    emit,
    join_room,
    send,
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
    session['token'] = auth['access_token']
    if not uid:
        raise ConnectionRefusedError
    # # fetch client sessilogger.info(uidon id
    emit('msg', 'welcome!', broadcast=True)
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
    redis_4.hset("sid_to_user", mapping=sid_all)
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
        data['artisan_id']
    )
    logger.debug(g_hash)
    # reduce geohash length to 6 charz
    # subscribe useto a topic named after this
    # truncated geohash

    def handle_updates(msg):
        print("booking payload ::", msg)
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
    if redis_2.exists(room):
        # remove from queue
        redis_2.delete(room)

        # assign artisan to booking
        assign_artisan_to_booking(data)

        # send updates to user
        payload = {
            'payload': data,
            'recipient': redis_4.hget(
                'booking_id_to_uid',
                data['booking_id']
            )
        }
        send_event('msg', payload, '/customer')
        # socketio.emit(
        #     'offer_accepted',
        #     payload['payload'],
        #     to=redis_4.hget("user_to_sid", payload['recipient']),
        #     namespace='/customer',
        #     callback=customer_event_ack
        # )

        # join_room(room, namespace='/chat')
    else:
        emit(
            'offer_close',
            messages.dynamic_msg(
                messages.BOOKING_CANCELED, "customer"
            ),
            namespace='/artisan',
            to=request.sid
        )


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
        raise DataValidationError(messages.SCHEMA_ERROR, e)

    room = data.booking_id

    # update status of booking
    update_booking_status(data)

    # remove from queue once canceled
    redis_2.delete(room)

    socketio.emit(
        'offer_canceled',
        messages.dynamic_msg(messages.BOOKING_CANCELED, "artisan"),
        to=room
    )


@socketio.on('arrived_location', namespace='/artisan')
@parse_event_data
@valid_auth_required
def handle_location_arrival(uid, data):
    """ triggered when artisan arrives at location """

    # update booking status
    update_booking_status(data)

    payload = {
        'payload': messages.ARTISAN_ARRIVES,
        'recipient': redis_4.hget(
            'booking_id_to_uid',
            data['booking_id']
        )
    }
    send_event('artisan_arrived', payload, '/customer')


@socketio.on('job_started', namespace='/artisan')
@parse_event_data
@valid_auth_required
def handle_job_begin(uid, data):
    """ triggered when artisan begins a job """
    from tasks.booking_tasks import job_start

    # parse data with schema
    schema = BookingStartSchema()

    try:
        data = schema.load(data)
    except Exception as e:
        raise DataValidationError(messages.SCHEMA_ERROR, e)

    print(uid)
    artisan = Artisan.query.get(uid)
    if artisan.booking.booking_id == data['booking_id']:
        try:
            job_start(data)
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
    else:
        raise InvalidBookingTransaction(
            f"Artisan with id {artisan.artisan_id} has not been assigned this order"
        )


@socketio.on('job_completed', namespace='/artisan')
@parse_event_data
@valid_auth_required
def handle_job_end(uid, data):
    """ triggered when artisan ends a job """
    from tasks.booking_tasks import job_end

    try:
        job_end(data)
    except Exception as e:
        logger.exception(e)
        emit("error", messages.INTERNAL_SERVER_ERROR, namespace='/artisan')
    else:
        send(messages.JOB_COMPLETED)


@socketio.on('update_job_type', namespace='/artisan')
@parse_event_data
@valid_auth_required
def update_job_type(uid, data):
    """ triggered when artisan needs to switch to contract type """
    from tasks.booking_tasks import update_job_type

    try:
        update_job_type(data)
    except Exception as e:
        logger.exception(e)
        emit("error", messages.INTERNAL_SERVER_ERROR, namespace='/artisan')


@socketio.on('msg', namespace='/chat')
@parse_event_data
@valid_auth_required
def send_chat_msg(uid, data):
    """sends message to chat room"""
    msg = data['msg']
    room = data['booking_id']
    socketio.emit('msg', msg, to=room, namespace='/chat')
