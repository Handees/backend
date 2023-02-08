from core import socketio
from tasks.booking_tasks import update_booking_status
from extensions import redis_2
from core.utils import (
    LOG_FORMAT, _level
)
from .. import messages

from flask import request
from flask_socketio import (
    emit,
    join_room,
    send
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


# @socketio.on('connect', namespace='/chat')
# def connect_chat():
#     join_room("room")
#     emit("msg-chat", "new {} person joined chat".format(request.sid), namespace='/chat')


@socketio.on('connect', namespace='/artisan')
def connect():
    # # fetch client session id
    emit('msg', 'welcome!', broadcast=True)
    logger.debug('new artisan {} client connection!'.format(request.sid))


@socketio.on('pong', namespace='/chat')
def pong_event(data):
    if data:
        print(data)
    print("PONG received!!")


@socketio.on('pong', namespace='/artisan')
def pong_event_artisan(data):
    if data:
        print(data)
    print("PONG received!!")


@socketio.on('location_update', namespace='/artisan')
def update_location(data):
    data = data.replace('\\n', '')
    data = eval(data)
    print(data, type(data))
    data = eval(data)
    print(data, type(data))
    # TODO: add data validation
    # update artisan location on redis
    room = data['artisan_id']
    join_room(room)

    psub = redis_2.pubsub()
    psub.unsubscribe('*')

    redis_2.geoadd(
        name=data['job_category'],
        values=(data['lon'], data['lat'], data['artisan_id'])
    )
    g_hash = redis_2.geohash(
        data['job_category'],
        data['artisan_id']
    )
    logger.debug(g_hash)
    # reduce geohash length to 6 char
    # subscribe user to a topic named after this
    # truncated geohash

    def handle_updates(msg):
        print("booking payload ::", msg)
        socketio.emit('new_offer', eval(msg['data']), to=room, namespace='/artisan')

    psub.subscribe(**{g_hash[0][:7]: handle_updates})

    psub.run_in_thread(sleep_time=.01)


@socketio.on('accept_offer', namespace='/artisan')
def get_updates(data):
    data = data.replace('\\n', '')
    data = eval(data)
    print(data, type(data))
    data = eval(data)
    print(data, type(data))
    """ triggered when artisan accepts offer """
    from tasks.booking_tasks import assign_artisan_to_booking

    room = data['booking_id']
    if redis_2.exists(room):
        # remove from queue
        redis_2.delete(room)

        # assign artisan to booking
        assign_artisan_to_booking(data)

        # send updates to user
        socketio.emit('msg', data, to=room, namespace='/customer')

        join_room(room, namespace='/chat')
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
def cancel_offer_artisan(data):
    """ triggered when artisan cancels offer """
    from schemas.bookings_schema import CancelBookingSchema

    schema = CancelBookingSchema()

    try:
        data = schema.load(data)
    except Exception as e:
        raise e

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
def handle_location_arrival(data):
    """ triggered when artisan arrives at location """

    room = data['booking_id']

    # update booking status
    update_booking_status(data)

    socketio.emit('artisan_arrived', messages.ARTISAN_ARRIVES, to=room, namespace='/customer')


@socketio.on('job_started', namespace='/artisan')
def handle_job_begin(data):
    """ triggered when artisan begins a job """
    from tasks.booking_tasks import job_start

    try:
        job_start(data)
    except Exception as e:
        logger.exception(e)
        emit("error", messages.INTERNAL_SERVER_ERROR, namespace='/artisan')
    else:
        send(messages.JOB_STARTED)


@socketio.on('job_completed', namespace='/artisan')
def handle_job_end(data):
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
def update_job_type(data):
    """ triggered when artisan needs to switch to contract type """
    from tasks.booking_tasks import update_job_type

    try:
        update_job_type(data)
    except Exception as e:
        logger.exception(e)
        emit("error", messages.INTERNAL_SERVER_ERROR, namespace='/artisan')


@socketio.on('msg', namespace='/chat')
def send_chat_msg(data):
    """sends message to chat room"""
    msg = data['msg']
    room = data['booking_id']
    socketio.emit('msg', msg, to=room, namespace='/chat')
