import os
import json
import pprint
import zlib
import datetime
import requests
import mimetypes
import subprocess

from loguru import logger
from flask import jsonify
from google.cloud import storage
from firebase_admin import messaging
from google.oauth2 import service_account
from werkzeug.http import HTTP_STATUS_CODES

from core import db


def is_serializable(obj):
    try:
        json.dumps(obj)
        return True
    except (TypeError, OverflowError):
        return False


def load_data(user_obj, many=False):
    from schemas.bookings_schema import BookingSchema
    if user_obj:
        data = BookingSchema(many=many)

        return data.dump(user_obj)


def error_response(status_code, message=None, data=None):
    payload = {
        'error': HTTP_STATUS_CODES.get(status_code, 'Unknown error')
    }
    if message:
        payload['message'] = message
    if data:
        payload['data'] = data
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


def load_env(gpair):
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
        print(headers)
        req = requests.get(
            url,
            headers=headers
        )
        pprint.pp(req.json())
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


def generate_presigned_url(
    bucket_name,
    object_name,
    action="upload",
    eta=15
):
    cred = service_account.Credentials.from_service_account_file(
        os.getenv('F_KEY')
    )
    storage_client = storage.Client(credentials=cred)
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(object_name)

    _method = "GET" if action == 'download' else 'PUT'
    kwargs = {
        'version': 'v4',
        'expiration': datetime.timedelta(minutes=eta),
        'method': _method
    }
    content_type, _ = mimetypes.guess_type(object_name)
    if not content_type:
        content_type = 'application/octet-stream'
    if _method == "PUT":
        kwargs['content_type'] = content_type

    url = blob.generate_signed_url(**kwargs)

    return url


CHARS = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
BASE = len(CHARS)


# def base62_encode(num):
#     if num == 0:
#         return '0'
#     base62 = ''
#     while num > 0:
#         num, rem = divmod(num, 62)
#         base62 = CHARS[rem] + base62
#     return base62
def base62_encode(n: int) -> str:
    """Encodes a positive integer into a Base62 string."""
    if n == 0:
        return "0"
    if n < 0:
        raise ValueError("Cannot encode negative numbers.")

    encoded = ""
    while n > 0:
        remainder = n % BASE
        encoded = CHARS[remainder] + encoded
        n //= BASE
    return encoded


def generate_unique_file_id(
    user_id: int,
    filename: str,
    blob_type: int
) -> str:
    """
    Generates a unique, fixed-length Base62 identifier for a file.

    The ID is composed of:
    - User ID (a numeric integer)
    - Filename hash (CRC32 converted to a 32-bit integer)
    - Blob type (Mapped to a small integer)

    Args:
        user_id (int): A numeric user ID.
        filename (str): The original filename string.
        blob_type (str): The blob type from the defined map.

    Returns:
        str: A fixed-length Base62 encoded string.
    """
    user_id_int = user_id

    # 2. Hash the filename using CRC32 to get a fixed-size integer (32 bits)
    filename_hash = zlib.crc32(filename.encode('utf-8'))
    blob_type_int = blob_type

    # 4. Combine all integers into a single, large integer for encoding
    # We use bitwise shifts to combine them:
    # 40 = 32 (CRC32) + 8 (blob_type)
    combined_int = (user_id_int << 40) | (filename_hash << 8) | blob_type_int

    # 5. Base62 encode the combined integer
    encoded_id = base62_encode(combined_int)

    # Pad the string to a fixed length (18 characters for 104 bits)
    return encoded_id.zfill(18)


def decode_file_id(encoded_id: str):
    """
    Decodes the unique file ID to retrieve the original data.

    Args:
        encoded_id (str): The Base62 encoded file ID string.

    Returns:
        A tuple containing (user_id_int, blob_type_string).
        The filename hash is also returned as a hex string.
    """
    # Decode Base62 to the combined integer
    decoded_num = base62_decode_number(encoded_id)

    # Use bitmasking and shifting to extract the original integers
    # The mask for the blob type is 2^8 - 1 = 255
    blob_type_int = decoded_num & 0xFF  # Extract the last 8 bits
    
    # The hash and UUID are shifted down
    hash_and_user_id = decoded_num >> 8
    
    # The mask for the hash is 2^32 - 1
    filename_hash_int = hash_and_user_id & ((1 << 32) - 1)
    user_id_int = hash_and_user_id >> 32
    
    # Convert extracted integers back to their original types
    decoded_blob_type = REVERSE_BLOB_TYPE_MAP.get(blob_type_int)
    
    # The hash itself is not reversible, but we can return its hex string
    decoded_hash_hex = hex(filename_hash_int)[2:].zfill(8)
    
    return user_id_int, decoded_blob_type, decoded_hash_hex


def send_notification(data, token, app=None):
    print("FCM TOKEN IS::", token)
    print("Input data", data)
    push_notification = messaging.Message(
        data=data,
        token=token
    )
    response = messaging.send(
        push_notification,
        app=app
    )
    return response


# --- Example Usage ---
# my_number = 1000000000
# encoded_number = base62_encode(my_number)
# print(f"Original Number: {my_number}")
# print(f"Base62 Encoded:  {encoded_number}")

# res = generate_unique_file_id()
# x = generate_unique_file_id(
#     2,
#     "cat.png",
#     2
# )
# print(x)


# def load_env(client, environment, gpair):
#     from google_crc32c import Checksum

#     parent = "projects/handees"
#     keys = []
#     res = []

#     # List all secrets.
#     for secret in client.list_secrets(request={"parent": parent}):
#         keys.append(secret.name)

#     # Build the resource name of the secret version.

#     for k in keys:
#         # Access the secret version.
#         name = f"projects/handees/secrets/{k}/versions/{environment}"
#         response = client.access_secret_version(request={"name": name})

#         # Verify payload checksum.
#         crc32c = Checksum()
#         crc32c.update(response.payload.data)
#         if response.payload.data_crc32c != int(crc32c.hexdigest(), 16):
#             raise Exception("Data corruption detected.")
#         else:
#             res.append(response)
#     return res


# url = "https://api.prembly.com/identitypass/verification/nin_w_face"

# payload = {
#     "number": 12345678909,
#     "image": "https://res.cloudinary.com/dh3i1wodq/image/upload/v1675417496/cbimage_3_drqdoc.jpg"
# }
# headers = {
#     "accept": "application/json",
#     "X-Api-Key": "sandbox_sk_bED6axRWzaWLLycBjIkyOVoyCaTyzSDk9L7Cc3H",
#     "app_id": "15c9a26e-4672-41bb-b53d-3764a25dedbd",
#     "content-type": "application/x-www-form-urlencoded"
# }

# response = requests.post(url, data=payload, headers=headers)

# print(response.text)