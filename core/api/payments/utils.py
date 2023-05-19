import requests
import hmac
import hashlib
from loguru import logger

from .messages import INVALID_PAYSTACK_HEADER


class PaystackClient:
    BASE_URL = "https://api.paystack.co"

    def __init__(self, secret):
        self.headers = {
            "Authorization": f"Bearer {secret}"
        }

    def append_to_headers(self, params):
        """ append to default headers """
        if type(params) == dict:
            self.headers = {
                **self.headers,
                **params
            }
            return self.headers
        else:
            logger.error(INVALID_PAYSTACK_HEADER)
            return

    def init_transaction(self, payload):
        """ init new transaction on paystack """

        logger.info("Attempting to initialize new transaction with Paystack ...")

        endpoint = "/transaction/initialize"
        try:
            req = requests.post(
                url=PaystackClient.BASE_URL + endpoint,
                json=payload,
                headers=self.headers
            )
        except Exception:
            raise Exception
        else:
            return req

    def init_refund(self, payload):
        """ initializes new refund """
        logger.info("Attempting to initialize new refund with Paystack ...")

        endpoint = "/refund"

        try:
            req = requests.post(
                url=PaystackClient.BASE_URL + endpoint,
                json=payload,
                headers=self.headers
            )
        except Exception:
            raise Exception
        else:
            return req


def gen_hmac_hash(payload, secret):
    """ paystack requires that we verify a header by comparing a hash signature

        read here for more info: https://paystack.com/docs/payments/webhooks
    """

    # reference : https://stackoverflow.com/questions/53910845/generate-hmac-sha256-signature-python
    skey = secret.encode("utf-8")
    try:
        new_hash = hmac.new(
            skey, payload.encode('utf-8'), hashlib.sha512
        ).hexdigest()
    except Exception as e:
        logger.exception(e)
    else:
        return new_hash
