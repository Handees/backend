from extensions import redis_
# TODO: map socket connections to channels

# TODO: subscribe artisans to channel (on connect) where they
# listen for new offers

# sockets map
# sockets_map = {}
# global sockets_map
# # check if socket id is part of channel
# if socket not in map:
#     sockets_map[socket] = {channel: True}
# sockets_map[socket][channel] = True


def subscribe(socket, channel):
    sub = redis_.pubsub()
    sub.subscribe(channel)


def publish(socket, channel, msg):
    # create channel and send message
    redis_.publish(f'{channel}', msg)



# TODO: create on_message handler