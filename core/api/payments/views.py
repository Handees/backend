from . import payments
from ..auth.auth_helper import (
    login_required,
    paystack_verification,
    role_required
)
from schemas.payment import InitTransactionSchema
from core.utils import (
    error_response,
    gen_response,
    setLogger
)
from .utils import (
    PaystackClient
)
from .messages import (
    PAYSTACK_ERROR,
    TRANSACTION_INITIATED
)
from tasks.payments import handlers

from flask import request
from loguru import logger
import os

logger.remove()
setLogger()


@payments.post('/')
@login_required
@role_required("customer")
def new_payment_transaction(current_user):
    payload = request.get_json(force=True)
    schema = InitTransactionSchema()
    try:
        data = schema.load(payload)
    except Exception:
        return error_response(
            400,
            message=schema.error_messages
        )
    else:
        # send request to paystack api
        client = PaystackClient(os.getenv('PAYSTACK_TEST_SECRET'))

        try:
            req = client.init_transaction(data)
        except Exception as e:
            logger.exception(e)
            return error_response(
                500,
                message=PAYSTACK_ERROR
            )
        else:
            body, status_code = req.json(), req.status_code
            if status_code == 200:
                if body['status'] is True:
                    return gen_response(
                        status_code=200,
                        message=TRANSACTION_INITIATED,
                        data=body['data']
                    )
                else:
                    logger.debug(body)
                    return error_response(
                        400,
                        message=PAYSTACK_ERROR,
                        data=body['data']
                    )
            else:
                logger.debug(body)
                return error_response(
                    req.status_code,
                    message=PAYSTACK_ERROR
                )


# paystack webhook
@payments.post('/wbhook')
@paystack_verification
def webhook(event):
    if event:
        init_task = handlers[event['event']]
        logger.info(init_task, dir(init_task))
        return {
            "status": True
        }, 200