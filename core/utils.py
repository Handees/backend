from flask import jsonify
from schemas.bookings_schema import BookingSchema
from werkzeug.http import HTTP_STATUS_CODES
import json
from core import db


def is_serializable(obj):
    try:
        json.dumps(obj)
        return True
    except (TypeError, OverflowError):
        return False


def load_data(user_obj, many=False):
    if user_obj:
        data = BookingSchema(many=many)

        return data.dump(user_obj)


def error_response(status_code, message=None, data=None):
    payload = {
        'error': HTTP_STATUS_CODES.get(status_code, 'Unknown error')
    }
    if message:
        payload['message'] = message
    response = jsonify(payload)
    response.status_code = status_code
    return response


def parse_error(error, data, **kwargs):
    msg = ""
    for k, v in error.messages.items():
        err = v[0]
        if "Missing data" in err:
            msg = f"{k}: Missing data for required field"
        else:
            msg = f"{k}: {error}"
        break
    return msg


def gen_response(
    status_code,
    data=None,
    message=None,
    many=False,
    schema=None
):
    """ generic helper to generate server response """
    payload = {
        'msg': message
    }
    if data:
        if schema:
            if many:
                payload['data'] = schema(many=True).dump(data)
            else:
                payload['data'] = schema().dump(data)
        else:
            if is_serializable(data):
                payload['data'] = data
    resp = jsonify(payload)
    resp.status_code = status_code

    return resp

    # TODO: make obj serializable either using custom utils or schema


def get_class_by_tablename(tablename):
    # https://stackoverflow.com/questions/11668355/sqlalchemy-get-model-from-table-name-this-may-imply-appending-some-function-to
    """Return class reference mapped to table.
        :param tablename: String with name of table.
        :return: Class reference or None.
    """
    for c in db.Model.registry._class_registry.values():
        if hasattr(c, '__tablename__') and c.__tablename__ == tablename:
            return c
