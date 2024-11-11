from .base import (
    BaseSQLAlchemyAutoSchema,
    BaseSchema
)
from models.payments import (
    Payment,
    CardAuth
)
from core import (
    db,
    ma
)

from marshmallow import pre_load


class PaymentSchema(BaseSQLAlchemyAutoSchema):
    class Meta:
        model = Payment
        dump_only = (
            'payment_id',
            'customer_id'
        )
        transient = True
        load_instance = True
        include_fk = True
        include_relationships = True


class CardAuthSchema(BaseSQLAlchemyAutoSchema):
    class Meta:
        model = CardAuth
        dump_only = (
            'id'
        )
        load_instance = True
        include_fk = True
        transient = True
        include_relationships = False

    @pre_load
    def pre_format_data(self, data, *args, **kwargs):
        if data:
            data['last_four'] = data['last4']
            del data['last4']
        return data


class FrontEndCardSchema(BaseSQLAlchemyAutoSchema):
    class Meta:
        model = CardAuth
        dump_only = (
            'id'
        )
        fields = (
            'account_name',
            'last_four',
            'exp_month',
            'exp_year',
            'signature',
        )


class PaymentEventSchema(BaseSchema):
    class Meta:
        model = Payment
        fields = (
            'amount',
            'transaction_id'
        )


class InitTransactionSchema(BaseSchema):
    amount = ma.Float(required=True)
    email = ma.Email(required=True)
