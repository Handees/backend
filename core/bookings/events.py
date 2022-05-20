from .. import socketio
from flask_socketio import send, emit
from flask import request
from extensions import redis_
# import pygeohash as pgh


@socketio.on('connect')
def connect():
    # # fetch client session id
    emit('msg', 'welcome!', broadcast=True)
    print('someone connected')
    # sid = request.sid
    # if sid:
    #     new_socket = Socket(sid=sid)
    #     db.session.add(new_socket)
    #     db.session.commit()
    # ghash = pgh.encode(data['lat'], data['lon'])
    # send(ghash, to=sid)


@socketio.on('location_update', namespace='/artisan')
def update_location(data):
    # update artisan location on redis
    redis_.geoadd(
        name="artisan_pos",
        values=(data['lat'], data['lon'], data['artisan_id'])
    )
    # sub = 
    # TODO: connect artisan to geohash pubsub channel


# #  option one
@socketio.on('order_updates')
def get_updates(data):
    from tasks.push_booking_to_queue import pbq
    # add client to special room
    room = request.sid
    # continually query celery for updates
    while True:
        task = pbq.AsyncResult(data['task_id'])
        if task.state == 'SUCCESS':
            result = task.info.get('match_profile')
            emit('request_update', result, to=room)
            break


@socketio.on('accept_offer')
def offer(data):
    room = request.sid
    # notify client of update
    # order =
    emit('message', data, to=room)
    print(data)


# @socketio.on('connect')
# def connect():
#     print('someone connected')
#     emit('welcome', 'welcome!', broadcast=True)

@socketio.on('test')
def test(data):
    print(data)
    emit('msg', 'test data', broadcast=True)
4