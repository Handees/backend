from core import socket
from flask_socketio import send
from flask import request
from core import db
from models.utils import Socket
from tasks.push_booking_to_queue import pbq
from extensions import redis_
import pygeohash as pgh


@socket.on('connect', namespace='/artisan')
def connect(data):
    # fetch client session id
    sid = request.sid
    if sid:
        new_socket = Socket(sid=sid)
        db.session.add(new_socket)
        db.session.commit()
    ghash = pgh.encode(data['lat'], data['lon'])
    send(ghash, to=sid)


@socket.on('location_update', namespace='/artisan')
def update_location(data):
    # update artisan location on redis
    redis_.geoadd(
        name="artisan_pos",
        values=(data['lat'], data['lon'], data['artisan_id'])
    )


#  option one
@socket.on('order_updates')
def get_updates(data):
    # add client to special room
    room = request.sid
    # continually query celery for updates
    while True:
        task = pbq.AsyncResult(data['task_id'])
        if task.state == 'SUCCESS':
            result = task.info.get('match_profile')
            send(result, to=room)
            break


@socket.on('accept_offer', namespace='/artisan')
def offer(data):
    # notify client of update
    # order =
    pass
