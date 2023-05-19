from schemas.bookings_schema import BookingSchema
from extensions import redis_
from core import socketio
from core.api.auth.auth_helper import verify_token

from flask import (
    jsonify,
    request,
    abort
)
from loguru import logger
import functools
from flask_socketio import (
    disconnect,
    ConnectionRefusedError
)
from flask import session
import json


def is_serializable(obj):
    try:
        json.dumps(obj)
        return True
    except (TypeError, OverflowError):
        return False


def gen_response(status_code, data, message=None, many=False, use_schema=False):
    """ generic helper to generate server response """
    payload = {
        'msg': message
    }
    if data:
        if use_schema:
            if many:
                payload['data'] = BookingSchema(many=True).dump(data)
            else:
                payload['data'] = BookingSchema().dump(data)
        else:
            if is_serializable(data):
                payload['data'] = data
    resp = jsonify(payload)
    resp.status_code = status_code

    return resp


def exit_cache(id):
    while redis_.get(id):
        redis_.delete(id)
    return redis_.get(id)


def parse_data(data):
    pass


def auth_param_required(f):
    @functools.wraps(f)
    def wrapped(*args, **kwargs):
        if len(args) < 1:
            logger.error("HEYY")
            socketio.emit(
                "msg",
                "Client error: Missing Auth param"
            )
            disconnect(sid=request.sid)
        else:
            logger.info("OMO")
            return f(*args, **kwargs)
    return wrapped


def valid_auth_required(f):
    @functools.wraps(f)
    def wrapped(*args, **kwargs):
        try:
            if 'token' in session:
                uid = verify_token(session.get('token'))
                print(uid)
                return f(uid, *args, **kwargs)
            else:
                print('WAHALA')
        except Exception as e:
            disconnect()
            print(str(e))
            raise ConnectionRefusedError(str(e))
    return wrapped
