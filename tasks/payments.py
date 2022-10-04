from .booking_tasks import huey
from models.payments import (
    Payment,
    CardAuth,
    db
)
from models.user_models import User
from core.exc import DataValidationError
from schemas.payment import CardAuthSchema
from config import config_options
from extensions import HueyTemplate

import uuid


@huey.task()
def create_transaction(data):
    app = HueyTemplate.get_flask_app(config_options['staging'])

    with app.app_context():
        pass

    pass


@huey.task()
def charge_sucess(data):
    # TODO: record transaction in database (making sure to add the transaction id)

    data = data['data']
    new_payment = Payment(
        transaction_id=data['id'],
        total_amount=data['amount'],
        status=True
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
            card_owner = User.get_by_email(data['data']['customer']['email'])
            new_card.user = card_owner
        except Exception as e:
            db.session.rollback()
            raise DataValidationError(schema.error_messages, e)
        else:
            db.session.commit()


handlers = {
    'charge.success': charge_sucess
}
