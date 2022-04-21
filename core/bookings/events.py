from core import socket
from flask_socketio import send
from flask import request
from core import db
from models.utils import Socket
from tasks.push_booking_to_queue import pbq


@socket.on('connect')
def connect():
    # fetch client session id
    sid = request.sid
    if sid:
        new_socket = Socket(sid=sid)
        db.session.add(new_socket)
        db.session.commit()


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
