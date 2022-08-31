from extensions import (
    HueyTemplate,
    redis_2
)
from config import BaseConfig


huey = HueyTemplate(config=BaseConfig.HUEY_CONFIG).huey


@huey.task()
def pbq(booking_details):
    # find nearest artisans to customer
    lat, lon = booking_details['lat'], booking_details['lon']
    redis_2.geoadd(
        name="customer_pos",
        values=(lon, lat, booking_details['user_id'])
    )
    g_hash = redis_2.geohash(
        'customer_pos',
        booking_details['user_id']
    )
    print(g_hash)
    print(g_hash[0][:7])

    redis_2.set(booking_details['booking_id'], str(booking_details))

    # broadcast message to artisans using a redis pub/sub channel
    # the channel is unique to each artisan and its id is synonymous
    # to the artisan's geohash
    redis_2.publish(g_hash[0][:7], str(booking_details))
