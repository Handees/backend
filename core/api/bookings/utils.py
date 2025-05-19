import json
import requests

from flask import jsonify
from loguru import logger
from dotenv import load_dotenv

from extensions import redis_, redis_5
from schemas.bookings_schema import BookingSchema

load_dotenv()


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


def count_nearby_artisans():
    keys = redis_5.keys('*')
    results = {}
    for key in keys:
        results[key] = redis_5.zcard(key)

    return results


class DistanceAPIClient:
    BASE_URL = "https://api-v2.distancematrix.ai/maps/api"

    def __init__(self, secret):
        self._key = secret

    def get_route_info(self, source, destination):
        endpoint = "/distancematrix/json"
        query = f"origins={source}&destinations={destination}"
        logger.error(f"{self.BASE_URL}{endpoint}?{query}&key={self._key}")
        try:
            req = requests.post(
                url=f"{self.BASE_URL}{endpoint}?{query}&key={self._key}"
            )
        except Exception:
            raise Exception
        else:
            return req
