from core import socketio
from extensions import (
    redis_,
    redis_4
)
from core.api.auth.auth_helper import (
    auth_param_required,
    valid_auth_required
)
from tasks.events import send_event
from core.exc import DataValidationError
from core.api.bookings.events.utils import parse_event_data
from schemas.bookings_schema import BookingStartSchema
from core.api.auth.auth_helper import verify_token
from tasks.booking_tasks import confirm_job_details
from .. import messages

from loguru import logger
from flask_socketio import emit, join_room
from flask import (
    request,
    session
)


@socketio.on('connect', namespace='/customer')
@auth_param_required
def connect(auth):
    uid = verify_token(auth['access_token'])
    if not uid:
        raise ConnectionRefusedError
    # fetch client session id
    session['uid'] = uid

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
    logger.debug('new customer {} client connection!'.format(request.sid))


@socketio.on('disconnect', namespace='/customer')
def disconnect():
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


@socketio.on('booking_update', namespace='/customer')
@parse_event_data
def booking_upate(data):
    room = data['booking_id']
    join_room(room)
    emit('chat_room', data)
    logger.info("added user to updates room {}".format(room))


@socketio.on('join_chat', namespace='/chat')
@parse_event_data
def enter_customer_artisan_chat(data):
    room = data['booking_id']
    join_room(room, namespace='/chat')


@socketio.on('cancel_offer', namespace='/customer')
@parse_event_data
def cancel_offer(data):
    room = data['artisan_id']

    # update state of offer in cache
    try:
        redis_.delete(data['booking_id'])
    except Exception as e:
        logger.error(e)

    logger.info('Client canceled; removing booking with id: {} from cache'.format(
        data['booking_id']
    ))
    socketio.emit(
        'offer_cancelled',
        "Client cancelled offer",
        namespace='/artisan',
        to=room
    )


@socketio.on('msg', namespace='/chat')
@parse_event_data
def send_chat_msg(data):
    """sends message to chat room"""
    msg = data['msg']
    room = data['booking_id']
    socketio.emit('msg', msg, to=room, namespace='/chat')


@socketio.on('test', namespace='/customer')
@parse_event_data
def sendstuff(msg):
    socketio.emit('msg', msg, namespace='/customer')


@socketio.on('confirm_job_details', namespace='/customer')
@parse_event_data
@valid_auth_required
def accept_job_details(uid, data):
    """ triggered when customer has confirmed job details """

    try:
        data = BookingStartSchema().load(data)
    except DataValidationError as e:
        logger.exception(e)
        emit("error", messages.SCHEMA_ERROR, namespace='/customer')

    try:
        confirm_job_details(data)
    except Exception as e:
        logger.exception(e)
        emit("error", messages.INTERNAL_SERVER_ERROR, namespace='/customer')


@socketio.on('reject_job_details', namespace='/customer')
@parse_event_data
@valid_auth_required
def reject_job_details(uid, data):
    """ triggered when customer has rejected job details """

    payload = {
        'payload': {'msg': messages.BOOKING_DETAILS_REJECTED},
        'recipient': redis_4.hget(
            'booking_id_to_artisan',
            data['booking_id']
        )
    }
    send_event(
        'job_details_rejected',
        payload,
        '/artisan'
    )

# {
#     "lat": 6.518139822341671,
#     "lon": 3.3995335371527604,
#     "artisan_id": "231984u384w9dushe238e"
# }

# // http://127.0.0.1:5020/artisan

# {
#     "lat": 6.517871336509268,
#     "lon": 3.399740067230001,
#     "user_id": "jksdhfuihewuiohio2"
# }
