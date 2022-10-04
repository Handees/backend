from .base import (
    TimestampMixin,
    BaseModelPR
)
from core import db
from .base import SerializableEnum


class PaymentMethodEnum(SerializableEnum):
    """ describes payment options """
    CASH = 1
    CARD = 2


class Payment(TimestampMixin, db.Model):
    payment_id = db.Column(db.String, primary_key=True)
    customer_id = db.Column(db.String, db.ForeignKey('user.user_id'))
    method = db.Column(
        db.Enum(PaymentMethodEnum),
        nullable=False,
        default=PaymentMethodEnum["CARD"]
    )
    total_amount = db.Column(db.Float)
    base_rate = db.Column(db.Float)
    surge_rate = db.Column(db.Float)
    tax = db.Column(db.Float)
    tip_amount = db.Column(db.Float)
    status = db.Column(db.Boolean, default=False)
    regulatory_charge = db.Column(db.Boolean, default=False)
    transaction_id = db.Column(db.BigInteger)
    order = db.relationship('Booking', backref='payment')
    # TODO: Add date dim


class CardAuth(BaseModelPR, TimestampMixin, db.Model):
    authorization_code = db.Column(db.String, unique=True)
    card_type = db.Column(db.String, index=True)
    last_four = db.Column(db.String)
    exp_month = db.Column(db.String)
    exp_year = db.Column(db.String)
    bin = db.Column(db.String)
    bank = db.Column(db.String, index=True)
    channel = db.Column(db.String)
    signature = db.Column(db.String, unique=True)
    reusable = db.Column(db.String)
    country_code = db.Column(db.String)
    account_name = db.Column(db.String)
    user_id = db.Column(db.String, db.ForeignKey('user.user_id'))

    @classmethod
    def get_by_card_type(cls, type):
        return cls.query.filter_by(card_type=type).first()

    @classmethod
    def get_by_bank(cls, bank):
        return cls.query.filter_by(bank=bank).first()

    @classmethod
    def get_by_signature(cls, signature):
        return cls.query.filter_by(signature=signature).first()
