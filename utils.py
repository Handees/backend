from schemas.bookings_schema import BookingSchema
from core import db

from flask import jsonify
from werkzeug.http import HTTP_STATUS_CODES
from loguru import logger
import json
import os
import requests
import subprocess
import pprint


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
    if data is not None:
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


# consts
LOG_FORMAT = "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | filename={name} function={function} line={line} msg={message} level={level: <8}"  # noqa
_level = "INFO" if os.getenv('APP_ENV').lower() in ['development', 'local'] \
    else "ERROR"


def setLogger():
    import sys
    from loguru import logger

    logger.remove()

    logger.add(
        sys.stderr,
        colorize=True,
        format=LOG_FORMAT,
        level=_level
    )


def fetch_instance_tag():
    # https://learn.microsoft.com/en-us/azure/virtual-machines/instance-metadata-service?tabs=linux
    """ fetches vm metadata including its tag """
    metadata_url = "http://169.254.169.254/metadata/instance?api-version=2021-02-01&format=json"

    headers = {'Metadata': 'true'}

    # Send the GET request to retrieve the instance metadata
    response = requests.get(metadata_url, headers=headers, proxies={})

    # Retrieve the tags from the response
    tags = response.json()['compute']['tags']

    # Print the tags
    return tags


def load_env_local(gpair):
    access_token = None

    if os.getenv('P_ENV').lower() == 'local':
        cmd = "gcloud auth print-access-token"
        keys = []
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True)

        if res.returncode == 0:
            access_token = res.stdout.strip()
    else:
        try:
            req = requests.get(
                url=os.getenv('AUTH_URL'),
                headers={
                    "Metadata-Flavor": "Google"
                }
            )
            if req.status_code != 200:
                raise Exception("Omo! Error request to fetch access token came back with (well not 200 😐)")
            access_token = req.json()['access_token']
        except Exception as e:
            logger.error("Ewo oo 🤷‍♂️ error occurred while trying to fetch access token")
            raise e

    project_id = "handees"
    url = "https://secretmanager.googleapis.com/v1/projects/{}/secrets".format(project_id)

    if access_token:
        headers = {
            "Authorization": "Bearer {}".format(access_token),
            "Content-Type": "application/json",
        }
        req = requests.get(
            url,
            headers=headers
        )
        if req.status_code == 200:
            pprint.pp(req.json())
            keys = [
                requests.get(
                    f"{url}/{obj['name'].split('/')[-1]}/versions/dev:access",
                    headers=headers
                ).json()
                for obj in req.json()['secrets']
            ]
            keys = [next(gpair(obj)) for obj in keys]
            pprint.pprint(keys)
        else:
            raise Exception("Error from API while trying to get secrets")
    else:
        raise Exception("Error generating token")

    return keys


def load_env(client, environment, gpair):
    from google_crc32c import Checksum

    parent = "projects/handees"
    keys = []
    res = []

    # List all secrets.
    for secret in client.list_secrets(request={"parent": parent}):
        keys.append(secret.name)

    # Build the resource name of the secret version.

    for k in keys:
        # Access the secret version.
        name = f"projects/handees/secrets/{k}/versions/{environment}"
        response = client.access_secret_version(request={"name": name})

        # Verify payload checksum.
        crc32c = Checksum()
        crc32c.update(response.payload.data)
        if response.payload.data_crc32c != int(crc32c.hexdigest(), 16):
            raise Exception("Data corruption detected.")
        else:
            res.append(response)
    return res
