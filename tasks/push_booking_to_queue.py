from core import celery
from extensions import redis_


@celery.task(bind=True, name='push_booking_to_queue.pbq')
def pbq(self, booking_details):
    # find nearest artisans to customer
    print("Taking over")
    lat, lon = booking_details['lat'], booking_details['lon']
    sub = redis_.pubsub()
    sub.subscribe(booking_details['booking_id'])
    r = 128
    near_client = redis_.geosearch(
        name="artisan_pos", latitude=lat,
        longitude=lon, radius=r, withdist=True
    )
    while len(near_client) < 3:
        r += 100
        near_client = redis_.geosearch(
            name="artisan_search", latitude=lat,
            longitude=lon, radius=r, withdist=True,
            withhash=True
        )
    # broadcast message to artisans using a redis pub/sub channel
    # the channel is unique to each artisan and its id is synonymous
    # to the artisan's geohash
    for artisan in near_client:
        redis_.publish(f'{artisan[1]}', booking_details)
    # listen for updates on the order
    for message in sub.listen():
        if message is not None and isinstance(message, dict):
            return {
                'match_profile': message['data']
            }
