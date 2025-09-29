import os
import uuid

from loguru import logger
from sqlalchemy import select

from .booking_tasks import huey
from .events import send_event
from models.payments import (
    Payment,
    CardAuth,
    WithdrawalAccounts,
    WalletTransaction,
    Withdrawals,
    WalletTransactionEnum,
    TransactionStatusEnum
)
from models.user_models import User, Artisan
from models.payments import PaymentStatusEnum
from core.exc import DataValidationError
from schemas.payment import (
    CardAuthSchema,
    FrontEndCardSchema
)
from config import config_options
from add_extensions import (
    HueyTemplate,
    redis_4
)
from utils import setLogger

logger.remove()
setLogger()


@huey.task()
def create_transaction(data):
    app = HueyTemplate.get_flask_app(config_options['staging'])

    with app.app_context():
        pass

    pass


@huey.task()
def initiate_refund(trans_id):
    from core.api.payments.utils import PaystackClient

    client = PaystackClient(os.getenv('PAYSTACK_TEST_SECRET'))
    try:
        req = client.init_refund({'transaction': trans_id})
        print(req.json(), req.status_code)
    except Exception as e:
        logger.exception(e)

    # TODO: Store refund transaction dets


@huey.task()
def charge_sucess(data):
    _huey = HueyTemplate()
    app = _huey.get_flask_app(config_options['development'])
    db = _huey.huey_db

    with app.app_context():
        # TODO: record transaction in database 
        # (making sure to add the transaction id)

        # if cardAuth with sigkey exists then this wouldn't
        #  be the first charge on the card (A.K.A its not a new card)
        card_authorization = data['authorization']
        _cauth = CardAuth.get_by_signature(
            card_authorization['signature'],
            session=db.session()
        )
        payment: Payment = db.session.query(Payment).filter_by(
            transaction_reference=data['reference']
        ).first()
        payment.status = PaymentStatusEnum.SUCCESS
        payment.transaction_id = data['id']
        if not _cauth:
            schema = CardAuthSchema()
            try:
                new_card = schema.load(card_authorization)
                # find owner by email
                card_owner = User.get_by_email(
                    data['customer']['email'],
                    session=db.session()
                )
                new_card.user = card_owner
                db.session.add(new_card)
                db.session.commit()

                # send signal to customer
                schema = FrontEndCardSchema()
                payload = {
                    'payload': {'data': schema.dump(new_card)},
                    'recipient': card_owner.user_id
                }
                send_event(
                    'new_card_added',
                    payload,
                    '/customer'
                )
            except Exception as e:
                db.session.rollback()
                logger.error(e)
                raise DataValidationError(schema.error_messages, e)
            finally:
                db.session.close()

            # initiate refund
            init_refund = initiate_refund(data['id'])
            logger.info(init_refund)

        try:
            db.session.commit()
        except Exception as e:
            logger.exception(e)
            db.session.rollback()
        finally:
            db.session.close()


@huey.task()
def initiate_charge(charge_data):
    # TODO: to consider is this should happen synchronously
    from core.api.payments.utils import PaystackClient
    from tasks.events import send_event

    _huey = HueyTemplate()
    app = _huey.get_flask_app(config_options['development'])
    db = _huey.huey_db

    with app.app_context():
        client = PaystackClient(os.getenv('PAYSTACK_TEST_SECRET'))
        user_rid = charge_data['customer_info']['user_rid']
        try:
            req = client.init_charge(charge_data['charge_info'])

            if req.status_code != 200 or not req.json()['status']:
                logger.error(f"PAYSTACK_ERROR: {req.text}")
                send_event(
                    'paystack_charge_error',
                    {
                        'recipient': user_rid,
                        'payload': {
                            'message': "An error occurred while trying to charge card",  # noqa: E501
                            'error': req.text
                        }
                    }
                )
                return
            # checks if charge is being challenged
            req = req.json()
            req = req['data']
            if 'pause' in req and req['paused']:
                # send the authorization URL to frontend
                send_event(
                    'paystack_authorization_routine',
                    {
                        'recipient': user_rid,
                        'payload': {
                            'authorization_url': req['authorization_url']
                        }
                    }
                )
            new_payment = Payment(
                total_amount=charge_data['charge_info']['amount'],
                status=PaymentStatusEnum['PENDING'],
                transaction_reference=req['reference']
            )
            new_payment.payment_id = uuid.uuid4().hex
            db.session.add(new_payment)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            logger.exception(e)


@huey.task()
def initiate_withdrawal(payload):
    from core.api.payments.utils import PaystackClient
    _huey = HueyTemplate()
    app = _huey.get_flask_app(config_options['development'])
    db = _huey.db
    client = PaystackClient(os.getenv('PAYSTACK_TEST_SECRET'))
    status_map = {
        'success': TransactionStatusEnum.SUCCESS,
        'pending': TransactionStatusEnum.PENDING,
        'reversed': TransactionStatusEnum.REVERSED,
        'failed': TransactionStatusEnum.FAILED
    }

    with app.app_context():
        with db.session() as sess:
            account = sess.scalar(
                select(WithdrawalAccounts).where(
                    id=payload['account_id']
                )
            )
            query = select(WalletTransaction).where(
                id=payload['wallet_transaction_id']
            )
            wallet_transaction = sess.scalar(query)
            transfer_code = None

            # initiate transfer
            reference = f"handees_trf_{uuid.uuid4().hex}"
            try:
                req = client.initiate_transfer(
                    payload={
                        'amount': payload['amount'],
                        'reference': reference,
                        'recipient': account.recipient_code
                    }
                )
                if req.status_code != 200 or not req.json()['status']:
                    logger.error(f"PAYSTACK_ERROR: {req.text}")
                    wallet_transaction.status = TransactionStatusEnum.ERROR
                    sess.commit()
                    return
                req = req.json()['data']
                wallet_transaction.status = status_map.get(
                    req['status'],
                    TransactionStatusEnum.FAILED
                )
                if req['status'].lower() != 'pending':
                    logger.error('An error occurred during transfer.. retry')
                transfer_code = req['transfer_code']
            except Exception as e:
                logger.exception(e)
                wallet_transaction.status = TransactionStatusEnum.ERROR
                sess.commit()
            finally:
                if transfer_code:
                    withdrawal = Withdrawals(
                        reference=reference,
                        transfer_code=transfer_code,
                        artisan_id=payload['artisan_id']
                    )
                    sess.add(withdrawal)
                    sess.commit()

                # send final transfer status to client
                send_event(
                    'withdrawal_status',
                    {
                        'recipient': payload['user_id'],
                        'payload': {
                            'status': wallet_transaction.name
                        }
                    }
                )

handlers = {
    'charge.success': charge_sucess
}
