import json
import uuid

from core import socketio, db
from add_extensions import (
    redis_,
    redis_2,
    redis_4,
    redis_7
)
from models import User, Chat, ChatMessage
from models.bookings import BookingStatusEnum
from core.api.auth.auth_helper import (
    auth_param_required,
    valid_auth_required
)
from tasks.events import send_event
from tasks.booking_tasks import update_booking_status
from core.exc import DataValidationError
from core.api.bookings.events.utils import parse_event_data
from schemas.bookings_schema import BookingStartSchema
from core.api.auth.auth_helper import verify_token
from tasks.booking_tasks import confirm_job_details
from .. import messages
from .utils import error_response

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
    user: User = User.query.filter_by(user_id=uid).first()
    # coords = auth['initialCoordinates']
    # lon, lat = coords['lon'], coords['lat']
    if not uid:
        raise ConnectionRefusedError('Invalid user credentials found')
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
    redis_4.hset(
        "user_to_fcm_token",
        mapping={uid: user.mobile_app_registration_token}
    )
    # get ghash
    # redis_2.geoadd(
    #     name="customer_pos",
    #     values=(lon, lat, uid)
    # )
    # g_hash_key = redis_2.geohash(
    #     'customer_pos',
    #     uid
    # )[0][:6]
    # emit(
    #     "nearby_counts",
    #     eval(redis_.hget('ghash_to_artisan_count', g_hash_key))
    # )
    # print(g_hash_key)
    logger.debug('new customer {} client connection!'.format(request.sid))


@socketio.on('connect', namespace='/chat')
@valid_auth_required
def enter_chat_namespace(uid):
    redis_4.hset(
        "user_to_chat_sid",
        mapping={uid: request.sid}
    )


@socketio.on('disconnect', namespace='/customer')
def disconnect(reason=None):
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
@valid_auth_required
def enter_customer_artisan_chat(uid, data):
    room = data['booking_id']
    join_room(room, namespace='/chat')


@socketio.on('cancel_offer', namespace='/customer')
@parse_event_data
@valid_auth_required
def cancel_offer(uid, data):
    room = data['booking_id']

    # update state of offer in cache
    try:
        redis_.delete(data['booking_id'])
    except Exception as e:
        logger.error(e)

    logger.info('Client canceled; removing booking with id: {} from cache'.format(
        data['booking_id']
    ))
    customer_id = redis_4.hget('booking_id_to_uid', room)
    if not redis_.exists(room):
        emit(
            'error',
            error_response(messages.BOOKING_UNAVAILABLE, uid)
        )
        return
    if customer_id != uid:
        emit(
            'error',
            error_response(messages.INVALID_CANCEL_OFFER, uid)
        )
        return
    payload = {
        'payload': "Client cancelled offer",
        'recipient': redis_4.hget(
            'booking_id_to_artisan',
            room
        )
    }
    send_event(
        'offer_cancelled',
        payload,
        '/artisan'
    )
    # update status of booking
    update_booking_status(
        {
            'status': BookingStatusEnum.CUSTOMER_CANCELLED,
            **data
        }
    )
    # if still in unmatched state
    redis_.delete(room)
    # if already matched
    redis_7.delete(room)


@socketio.on('message', namespace='/chat')
@valid_auth_required
@parse_event_data
def send_chat_msg(uid, data):
    """sends message to chat room"""
    # check if chat exists in db if not create one
    with db.session() as sess:
        bk_id = data['booking_id']
        new_msg = ChatMessage(**data['chat_object'])
        sid = redis_4.hget('user_to_chat_sid', uid)
        chat_id = redis_4.hget('booking_id_to_chat_id', bk_id)
        if not chat_id:
            new_chat = Chat(booking_id=bk_id)
            sess.add(new_chat)
            chat_id = uuid.uuid4().hex
            new_chat.id = chat_id
            # set in cache
            redis_4.hset('booking_id_to_chat_id', bk_id, chat_id)
        sess.add(new_msg)
        sess.commit()
        room = data['booking_id']
        msg = json.dumps(data['chat_object'])
        socketio.send(msg, to=room, skip_sid=sid, namespace='/chat')


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
    # TODO: add check for already confirmed jobs
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
