from schemas.bookings_schema import BookingSchema
from flask import jsonify
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
