from .. import socketio
from flask_socketio import send, emit, join_room
from flask import request
from extensions import redis_
# import pygeohash as pgh


@socketio.on('connect')
def connect():
    # # fetch client session id
    emit('msg', 'welcome!', broadcast=True)
    print('someone connected')


@socketio.on('location_update', namespace='/artisan')
def update_location(data):
    # update artisan location on redis
    redis_.geoadd(
        name="artisan_pos",
        values=(data['lon'], data['lat'], data['artisan_id'])
    )
    g_hash = redis_.geohash(
        'artisan_pos',
        data['artisan_id']
    )
    print(g_hash)
    room = g_hash[0]
    join_room(room)
    print("DONE !")


@socketio.on('booking_update')
def booking_upate(data):
    room = data['booking_id']
    join_room(room)
    print("added user to updates room")


# #  option one
@socketio.on('order_updates')
def get_updates(data):
    room = data['booking_id']
    send(data, to=room)


@socketio.on('test')
def test(data):
    print(data)
    emit('msg', 'test data', broadcast=True)
