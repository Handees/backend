from .. import socketio
from flask_socketio import send, emit, join_room, rooms
from flask import request
from extensions import redis_
# import pygeohash as pgh


@socketio.on('connect', namespace='/artisan')
def connect():
    # # fetch client session id
    emit('msg', 'welcome!', broadcast=True)
    print('someone connected')


@socketio.on('location_update', namespace='/artisan')
def update_location(data):
    # update artisan location on redis
    room = data['artisan_id']
    join_room(room)

    psub = redis_.pubsub()
    psub.unsubscribe('*')

    redis_.geoadd(
        name="artisan_pos",
        values=(data['lon'], data['lat'], data['artisan_id'])
    )
    g_hash = redis_.geohash(
        'artisan_pos',
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


@socketio.on('booking_update')
def booking_upate(data):
    room = data['booking_id']
    join_room(room)
    print("added user to updates room")


# #  option one
@socketio.on('order_updates', namespace='/artisan')
def get_updates(data):
    room = data['booking_id']
    send(data, to=room)


@socketio.on('join', namespace='/artisan')
def test(data):
    print(data)
    join_room(data)
    emit('message', 'welcome to room')
    print(rooms(request.sid))


@socketio.on('message', namespace='/artisan')
def sumn(data):
    print(data, end="---")


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