import os
import json
import uuid

from flask import (
    request,
    render_template
)
from loguru import logger
from sqlalchemy.exc import IntegrityError

from . import payments
from core.extensions import db
from ..auth.auth_helper import (
    login_required,
    permission_required,
    role_required,
    paystack_verification
)
from schemas.payment import (
    InitTransactionSchema,
    PaymentSchema,
    ResolveAccountNumberSchema,
    WithdrawalAccountSchema,
    BankListSchema
)
from models.user_models import Permission
from models.payments import (
    Payment,
    WithdrawalAccounts
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


logger.remove()
setLogger()


@payments.post('/')
@login_required
@permission_required(Permission.make_payments)
def new_payment_transaction(current_user):
    ENV = os.getenv('APP_ENV', 'DEV')
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
        client = PaystackClient(
            os.getenv(f'PAYSTACK_{ENV}_SECRET')
        )

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


@payments.get('/banks/')
def get_banks():
    ENV = os.getenv('ENV', 'DEV')
    client = PaystackClient(
        os.getenv(f'PAYSTACK_{ENV}_SECRET')
    )
    req = client.list_banks()
    if req.status_code == 200:
        body = req.json()
        if body['status'] is True:
            banks = body['data']
            return gen_response(
                200,
                data=banks,
                schema=BankListSchema,
                many=True
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


@payments.post('/banks/resolve')
@login_required
@role_required('artisan')
def resolve_account(current_user):
    with db.session() as sess:
        schema = ResolveAccountNumberSchema()
        try:
            data = schema.load(request.get_json(force=True))
        except Exception as e:
            return gen_response(400, message=str(e))
        else:
            ENV = os.getenv('ENV', 'DEV')
            client = PaystackClient(
                os.getenv(f'PAYSTACK_{ENV}_SECRET')
            )
            req = client.resolve_account_number(data)
            if req.status_code == 200:
                body = req.json()
                if body['status'] is True:
                    recipient_data = {
                        'type': 'nuban',
                        'name': body['data']['account_name'],
                        'account_number': body['data']['account_number'],
                        'bank_code': data['bank_code'],
                        'currency': 'NGN'
                    }
                    nreq = client.create_transfer_recipient(recipient_data)
                    nbody = nreq.json()
                    if nreq.status_code not in (200, 201):
                        logger.exception(nreq.text)
                        return error_response(
                            req.status_code,
                            data=nreq.text,
                            message=PAYSTACK_ERROR
                        )
                    elif nreq.status_code == 200 and \
                            not nbody['data']['status']:
                        logger.exception(nbody)
                        return error_response(
                            400,
                            message=PAYSTACK_ERROR,
                            data=body['data']
                        )

                    # parse input
                    recipient_data.pop("type")
                    recipient_data['account_name'] = \
                        body['data']['account_name']
                    recipient_data['bank_name'] = \
                        nbody['data']['details']['bank_name']
                    recipient_data.pop('name')
                    recipient_data.pop('currency')

                    # store dets
                    new_account = WithdrawalAccounts(
                        **recipient_data,
                        recipient_code=nbody['data']['recipient_code']
                    )
                    new_account.artisan = current_user.artisan_profile
                    sess.add(new_account)
                    resp = gen_response(
                        200, data=new_account,
                        schema=WithdrawalAccountSchema
                    )
                    try:
                        sess.commit()
                    except IntegrityError as e:
                        logger.error(e)
                        return error_response(
                            status_code=400,
                            message="Likely, possibly, you're trying to add "
                            "data that already exists"
                        )
                    except Exception as e:
                        logger.error(e)
                        sess.rollback()
                        return error_response(
                            status_code=400,
                            message=str(e)
                        )
                    return resp
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
