from flask_socketio import emit
from wsgi import celery


@celery.task(bind=True, name='push_booking_to_queue.pbq')
def pbq(booking_details):
    # TODO: find nearest artisans to customer
    # TODO: create channel and add subscribe each one to the channel
    # TODO: subscribe to a channel to listen for updates on
    # TODO: once message is received from channel forward updates
    # via the socket to the client
    emit(booking_details, namespace='/artisans')
