from .base import BaseSQLAlchemyAutoSchema
from models.payments import Payment
from core import db


class PaymentSchema(BaseSQLAlchemyAutoSchema):
    class Meta:
        model = Payment
        dump_only = (
            'payment_id',
            'customer_id'
        )
        sqla_session = db.session
        load_instance = True
        include_fk = True
        include_relationships = True
