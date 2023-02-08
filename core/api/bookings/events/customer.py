from core import socketio
from extensions import redis_

from loguru import logger
from flask_socketio import emit, join_room
# import pygeohash as pgh


# @socketio.on('connect', namespace='/chat')
# def connect_chat():
#     logger.info('artisan socket joined chat namespace')
#     emit('msg', 'welcome! to chat', broadcast=True)


@socketio.on('connect', namespace='/customer')
def connect():
    # # fetch client session id
    emit('msg', 'welcome! customer', broadcast=True)
    logger.info('new client connected')


@socketio.on('booking_update', namespace='/customer')
def booking_upate(data):
    room = data['booking_id']
    join_room(room)
    emit('chat_room', data)
    logger.info("added user to updates room {}".format(room))


@socketio.on('join_chat', namespace='/chat')
def enter_customer_artisan_chat(data):
    room = data['booking_id']
    join_room(room, namespace='/chat')


# @socketio. on('close_offer')
# def close_offer(data):
#     room = data['booking_id']

#     # update state of offer in cache
#     redis_.delete(room)


@socketio.on('cancel_offer', namespace='/customer')
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
    socketio.emit('offer_canceled', "Client cancelled offer", namespace='/artisan', to=room)


@socketio.on('msg', namespace='/chat')
def send_chat_msg(data):
    """sends message to chat room"""
    msg = data['msg']
    room = data['booking_id']
    socketio.emit('msg', msg, to=room, namespace='/chat')


@socketio.on('test', namespace='/customer')
def sendstuff(msg):
    socketio.emit('msg', msg, namespace='/customer')


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
