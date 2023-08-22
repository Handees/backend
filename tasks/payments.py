from .booking_tasks import huey
from models.payments import (
    Payment,
    CardAuth,
    db
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
def charge_sucess(data):
    app = HueyTemplate.get_flask_app(config_options['staging'])

    with app.app_context():
        # TODO: record transaction in database (making sure to add the transaction id)
        new_payment = Payment(
            transaction_id=data['id'],
            total_amount=data['amount'],
            status=PaymentStatusEnum['SUCCESS']
        )
        new_payment.payment_id = uuid.uuid4().hex
        db.session.add(new_payment)

        # if cardAuth with sigkey exists then this wouldn't be the first charge on the card
        # (A.K.A its not a new card)
        card_authorization = data['authorization']
        _cauth = CardAuth.get_by_signature(
            card_authorization['signature']
        )
        if not _cauth:
            new_payment.regulatory_charge = True
            schema = CardAuthSchema()
            try:
                new_card = schema.load(card_authorization)

                # find owner by email
                card_owner = User.get_by_email(data['customer']['email'])
                new_card.user = card_owner
            except Exception as e:
                db.session.rollback()
                raise DataValidationError(schema.error_messages, e)
            else:
                db.session.commit()


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


handlers = {
    'charge.success': charge_sucess,
    'initate_refund': initiate_refund
}
