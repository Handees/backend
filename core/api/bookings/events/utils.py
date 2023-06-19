from functools import wraps
from flask_socketio import emit
from loguru import logger
import time

from extensions import redis_4
from core.exc import ClientNotConnected
from utils import setLogger


setLogger()


def send_event(fn):
    @wraps(fn)
    def decorated(*args, delay=2, backoff=1.15, retries=3, **kwargs):
        # check if receiver is connected
        try:
            if 'data' in kwargs:
                data = kwargs['data']
                user_sid = redis_4.hget("user_to_sid", data['recipient'])
                if not redis_4.exists(user_sid):
                    print(data['recipient'])
                    raise ClientNotConnected("Client no longer connected")
        except ClientNotConnected:
            logger.info('Retrying event since client not connected')
            while retries:
                time.sleep(delay)
                delay *= backoff
                retries -= 1
                emit(
                    kwargs['event'],
                    data['payload'],
                    to=data['recipient'],
                    namespace=kwargs['namespace']
                )
        return fn(*args, delay=2, backoff=1.15, retries=3, **kwargs)
    return decorated


def customer_event_ack(ack):
    print(ack)


def parse_event_data(fn):
    @wraps(fn)
    def decorated(*args):
        import json
        import os
        from dotenv import load_dotenv
        load_dotenv()
        if os.getenv('P_ENV') == 'local' or 'local' in args[0]:
            data, *other_args = args
            data = json.loads(data)
            data = eval(data)
            del data['local']
            return fn(data, *other_args)
    return decorated


def error_response(msg, uid):
    return {
        'payload': {'msg': msg},
        'recipient': uid
    }
