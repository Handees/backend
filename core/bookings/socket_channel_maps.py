from core import redis
# TODO: map socket connections to channels

# TODO: subscribe artisans to channel (on connect) where they
# listen for new offers

# sockets map
sockets_map = {}


def subscribe(socket, channel):
    global sockets_map
    # check if socket id is part of channel
    if socket not in map:
        sockets_map[socket] = {channel: True}
    sockets_map[socket][channel] = True
    # create channel
    # redis.publish(f'')
