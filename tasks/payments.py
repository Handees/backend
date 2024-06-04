from .booking_tasks import huey
from models.payments import (
    Payment,
    CardAuth
)
from models.user_models import User
from models.payments import PaymentStatusEnum
from core.exc import DataValidationError
from schemas.payment import CardAuthSchema
from config import config_options
from extensions import HueyTemplate
from utils import setLogger

import uuid
import os
from loguru import logger

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
        if not _cauth:
            new_payment = Payment(
                total_amount=data['amount'],
                transaction_id=data['id'],
                status=PaymentStatusEnum['SUCCESS'],
                regulatory_charge=True
            )
            new_payment.payment_id = uuid.uuid4().hex
            db.session.add(new_payment)
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
            except Exception as e:
                db.session.rollback()
                logger.error(e)
                raise DataValidationError(schema.error_messages, e)

            # initiate refund
            init_refund = initiate_refund(data['id'])
            logger.info(init_refund)
        else:
            payment: Payment = db.session.query(Payment).filter_by(
                transaction_reference=data['reference']
            ).first()
            payment.status = PaymentStatusEnum.SUCCESS
            payment.transaction_id = data['id']
            try:
                db.session.commit()
            except Exception as e:
                logger.exception(e)
                db.session.rollback()
            finally:
                db.session.close()


@huey.task()
def initiate_charge(charge_data):
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
                logger.error(
                    f"""
                        PAYSTACK_ERROR: The following error occurred while trying
                        to charge the card with auth id
                        {charge_data['charge_info']['authorization_code']}: \n
                    """
                )
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


handlers = {
    'charge.success': charge_sucess
}
