from core import socketio
from flask_socketio import emit, join_room
from extensions import redis_


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

    psub = redis_.pubsub()
    psub.unsubscribe('*')

    redis_.geoadd(
        name=data['job_category'],
        values=(data['lon'], data['lat'], data['artisan_id'])
    )
    g_hash = redis_.geohash(
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
    print(redis_.exists(room))
    if redis_.exists(room):

        # assign artisan to booking
        res = assign_artisan_to_booking(data)

        print(res())

        # send updates to user
        socketio.emit('msg', data, to=room)
    else:
        emit('offer_close', "The offer is no longer available", namespace='/artisan')


@socketio.on('cancel_offer', namespace='/artisan')
def cancel_offer_artisan(data):
    """ triggered when artisan cancels offer """

    room = data['booking_id']

    socketio.emit('offer_canceled', "Artisan canceled offer", to=room)
