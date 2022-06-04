from core import celery
from extensions import redis_
from core import socketio


@celery.task(bind=True, name='push_booking_to_queue.pbq')
def pbq(self, booking_details):
    # find nearest artisans to customer
    print("Taking over")
    lat, lon = booking_details['lat'], booking_details['lon']
    r = 128
    near_client = redis_.geosearch(
        name="artisan_pos", latitude=lat,
        longitude=lon, radius=r, withdist=True,
        withhash=True
    )
    print(near_client, end=" initial search")
    while len(near_client) < 3:
        r += 100
        near_client = redis_.geosearch(
            name="artisan_search", latitude=lat,
            longitude=lon, radius=r, withdist=True,
            withhash=True
        )
        print(near_client, r)
    # broadcast message to artisans using a redis pub/sub channel
    # the channel is unique to each artisan and its id is synonymous
    # to the artisan's geohash
    for artisan in near_client:
        ghash = redis_.geohash(
            'artisan_pos',
            artisan[0]
        )
        socketio.emit('service_request', booking_details, to=ghash, namespace='/artisan')
