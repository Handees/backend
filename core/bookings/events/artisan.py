from core import socketio
from tasks.booking_tasks import update_booking_status
from extensions import redis_2
from core.utils import (
    LOG_FORMAT, _level
)

from flask import request
from flask_socketio import emit, join_room
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


@socketio.on('connect', namespace='/artisan')
def connect():
    # # fetch client session id
    emit('msg', 'welcome!', broadcast=True)
    print('someone connected')


@socketio.on('location_update', namespace='/artisan')
def update_location(data):
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
    print(g_hash)
    # reduce geohash length to 6 char
    # subscribe user to a topic named after this
    # truncated geohash

    def handle_updates(msg):
        print("booking payload ::", msg)
        socketio.emit('msg', eval(msg['data']), room=room, namespace='/artisan')

    psub.subscribe(**{g_hash[0][:7]: handle_updates})

    psub.run_in_thread(sleep_time=.01)


@socketio.on('accept_offer', namespace='/artisan')
def get_updates(data):
    """ triggered when artisan accepts offer """
    from tasks.booking_tasks import assign_artisan_to_booking

    room = data['booking_id']
    if redis_2.exists(room):
        # remove from queue
        redis_2.delete(room)

        # assign artisan to booking
        assign_artisan_to_booking(data)

        # send updates to user
        socketio.emit('msg', data, to=room)
    else:
        emit(
            'offer_close',
            "The offer is no longer available",
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

    socketio.emit('offer_canceled', "Artisan canceled offer", to=room)


@socketio.on('arrived_location', namespace='/artisan')
def handle_location_arrival(data):
    """ triggered when artisan arrives at location """

    room = data['booking_id']

    # update booking status
    update_booking_status(data)

    socketio.emit('artisan_arrived', "Artisan has reached client location", to=room)


@socketio.on('job_started', namespace='/artisan')
def handle_job_begin(data):
    """ triggered when artisan begins a job """
    from tasks.booking_tasks import job_start

    try:
        job_start(data)
    except Exception as e:
        logger.exception(e)


@socketio.on('job_completed', namespace='/artisan')
def handle_job_end(data):
    """ triggered when artisan ends a job """
    from tasks.booking_tasks import job_end

    try:
        job_end(data)
    except Exception as e:
        logger.exception(e)
