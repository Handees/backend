import os
import json
import logging
import functools

import firebase_admin
from loguru import logger
from dotenv import load_dotenv

from add_extensions import redis_4
from .booking_tasks import huey
from firebase_admin import messaging
from core.exc import ClientNotConnected

load_dotenv()

# config
logging.basicConfig(level=logging.DEBUG)
redis_pass = os.getenv('REDIS_PASS')
redis_port = os.getenv('REDIS_PORT', 6378)

IMPORTANT_NOTIFICATIONS = [
    'approve_booking_details',
    'job_completed',
    'booking_offer_accepted',
    'offer_cancelled',
    'artisan_arrived', 'job_details_rejected',
    'artisan_clocked_in', 'artisan_clock_out',
    'job_started', 'approve_booking_details'
]


def exp_backoff_task(retries, retry_backoff):
    def deco(fn):
        @functools.wraps(fn)
        def inner(*args, **kwargs):
            # We will register this task with `context=True`, which causes
            # Huey to pass the task instance as a keyword argument to the
            # decorated task function. This enables us to modify its retry
            # delay, multiplying it by our backoff factor, in the event of
            # an exception.
            task = kwargs.pop('task')
            try:
                return fn(*args, **kwargs)
            except ClientNotConnected as exc:
                task.retry_delay *= retry_backoff
                raise exc

        # Register our wrapped task (inner()), which handles delegating to
        # our function, and in the event of an unhandled exception,
        # increases the retry delay by the given factor.
        return huey.task(retries=retries, retry_delay=2, context=True)(inner)
    return deco


@exp_backoff_task(retries=3, retry_backoff=1.5)
def send_event(event, data, namespace):
    logger.info(f"ATTEMPTING TO SEND EVENT: {event}")
    from flask_socketio import SocketIO
    from . import F_KEY_PATH

    print(F_KEY_PATH, "Firebase KEY")
    # print(d)

    if not data or not data['recipient']:
        logger.error("Cannot send event: No data received, or recipient missing")
        return

    # check if receiver is connected
    if not redis_4.hexists("user_to_sid", data['recipient']):
        logger.warning("client not connected: retrying...")
        raise ClientNotConnected("Client no longer connected")

    user_sid = redis_4.hget("user_to_sid", data['recipient'])

    if not redis_4.exists(user_sid):
        logger.warning("client not connected: retrying...")
        raise ClientNotConnected("Client no longer connected")

    app_instance = firebase_admin.get_app(name="firebase_admin_huey")
    mq = f"redis://:{redis_pass}@{os.getenv('REDIS_HOST')}:{redis_port}/7"
    sock = SocketIO(
        cors_allowed_origins=[
            'http://127.0.0.1:5020', 'http://127.0.0.1:5501',
            'https://www.piesocket.com'
        ],
        message_queue=mq,
        async_mode='gevent',
        logger=True,
        engineio_logger=True
    )
    resp = sock.emit(
        event,
        data['payload'],
        to=user_sid,
        namespace=namespace
    )
    if event in IMPORTANT_NOTIFICATIONS:
        notification_payload = {k: json.dumps(v) for k, v in data['payload'].items()}
        fcm_token = redis_4.hget("user_to_fcm_token", data['recipient'])
        print("FCM TOKEN IS::", fcm_token)
        print("Input data", notification_payload)
        # try:
        push_notification = messaging.Message(
            data=notification_payload,
            token=fcm_token
        )
        response = messaging.send(
            push_notification,
            app=app_instance
        )
        logger.error(f"Sent push notification request, with resp: {response}")
