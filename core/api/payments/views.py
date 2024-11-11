import os
import json
import uuid

from . import payments
from core.extensions import db
from ..auth.auth_helper import (
    login_required,
    permission_required,
    paystack_verification,
    role_required
)
from schemas.payment import (
    InitTransactionSchema,
    PaymentSchema
)
from models.user_models import Permission
from models.payments import (
    Payment,
    PaymentStatusEnum
)
from utils import (
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

from flask import (
    request,
    render_template
)
from loguru import logger


logger.remove()
setLogger()


@payments.post('/')
@login_required
@role_required("customer")  # TODO: make this support more roles
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
            status_code = req.status_code
            if status_code == 200:
                body = req.json()
                if body['status'] is True:
                    body = body['data']
                    new_payment = Payment(
                        total_amount=data['amount'],
                        transaction_reference=body['reference']
                    )
                    new_payment.payment_id = uuid.uuid4().hex
                    db.session.add(new_payment)
                    try:
                        db.session.commit()
                    except Exception as e:
                        logger.exception(e)
                        db.session.rollback()
                    finally:
                        db.session.close()
                    return gen_response(
                        status_code=200,
                        message=TRANSACTION_INITIATED,
                        data=body
                    )
                else:
                    logger.exception(body)
                    return error_response(
                        400,
                        message=PAYSTACK_ERROR,
                        data=body['data']
                    )
            else:
                logger.exception(req.text)
                return error_response(
                    req.status_code,
                    message=PAYSTACK_ERROR
                )


@payments.get('/')
@login_required
@permission_required(Permission.service_request)
def fetch_customer_transactions(current_user):
    transactions = current_user.payments
    schema = PaymentSchema(many=True)
    return gen_response(
        200,
        data=schema.dump(transactions)
    )


# paystack webhook
@payments.post('/wbhook')
@paystack_verification
def webhook(event):
    if event:
        logger.info("Event from paystack received")
        event = json.loads(event)
        event_name = event['event']
        if event_name.lower().strip() in handlers:
            init_card_auth = handlers[event_name](event['data'])

            logger.info(init_card_auth, dir(init_card_auth))
    return {
        "status": True
    }, 200


# callback for authorization challenge
@payments.get('/charge_callback')
@paystack_verification
def charge_callback(data=None):
    return render_template(
        """
        <!DOCTYPE html>
        <html>
        <head>
        <title>Popup Message</title>
        <style>
            body {
            text-align: center;
            font-family: sans-serif;
            margin: 0; /* Remove default margin */
            }
        </style>
        </head>
        <body>
        <p>You may close this popup and head back to the app</p>
        </body>
        </html>
        """
    ), 200


@payments.get('/testcharge')
def test():
    from schemas.payment import FrontEndCardSchema, CardAuth
    cauth = CardAuth.query.get(9)
    print(FrontEndCardSchema().dump(cauth))
    return {}, 200
