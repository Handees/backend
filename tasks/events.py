import os
import json
import logging
import functools

import firebase_admin
from loguru import logger
from dotenv import load_dotenv
from flask_socketio import SocketIO

from utils import send_notification
from add_extensions import redis_4
from .booking_tasks import huey
from core.exc import ClientNotConnected

load_dotenv()

# config
logging.basicConfig(level=logging.DEBUG)
redis_pass = os.getenv('REDIS_PASS')
redis_port = os.getenv('REDIS_PORT', 6378)

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

NOTIFICATONS_MAP = {
    'approve_booking_details': {
        'body': 'Kindly review service request details',
        'title': 'Approve Service Request Details'
    },
    'job_completed': {
        'body': "Artisan says their done with the work 😊",
        'title': 'Job Completed'
    },
    'booking_offer_accepted': {
        'body': "Hey you've been matched with an artisan near you!",
        'title': 'Booking Request Accepted'
    },
    'offer_cancelled': {
        'body': "Service request canceled💀",
        'title': 'Offer Has Been Canceled'
    },
    'artisan_arrived': {
        'body': "Good news! You have a visitor!🔥 Your artisan has arrived",
        'title': 'Artisan Has Arrived'
    },
    'job_details_rejected': {
        'body': "Customer rejected booking details💀 - contact them!",
        'title': 'Service Request Detail Rejected'
    },
    'artisan_clocked_in': {
        'body': 'Artisan clocked in for a work session',
        'title': 'Artisan Clocked In'
    },
    'artisan_clocked_out': {
        'body': 'Artisan clocked out from a work session',
        'title': 'Artisan Clocked Out'
    },
    'job_started': {
        'body': 'Service rendering has officialy begun✅',
        'title': 'Artisan Started Working'
    }
}


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
    resp = sock.emit(
        event,
        data['payload'],
        to=user_sid,
        namespace=namespace
    )
    print(f"SOCKET EMIT RESPONSE {resp}")
    if event in NOTIFICATONS_MAP:
        notification_payload = {
            k: json.dumps(v) for k, v in data['payload'].items()
        }
        fcm_token = redis_4.hget("user_to_fcm_token", data['recipient'])
        res = send_notification(
            notification_payload,
            fcm_token,
            app_instance,
            NOTIFICATONS_MAP[event]
        )
        logger.error(f"Sent push notification request, with resp: {res}")
