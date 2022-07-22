from extensions import HueyTemplate, redis_
from config import BaseConfig

huey = HueyTemplate(config=BaseConfig.HUEY_CONFIG).huey


@huey.task()
def pbq(booking_details):
    # find nearest artisans to customer
    lat, lon = booking_details['lat'], booking_details['lon']
    redis_.geoadd(
        name="customer_pos",
        values=(lon, lat, booking_details['user_id'])
    )
    g_hash = redis_.geohash(
        'customer_pos',
        booking_details['user_id']
    )
    print(g_hash)
    print(g_hash[0][:7])
    # broadcast message to artisans using a redis pub/sub channel
    # the channel is unique to each artisan and its id is synonymous
    # to the artisan's geohash
    redis_.publish(g_hash[0][:7], str(booking_details))
