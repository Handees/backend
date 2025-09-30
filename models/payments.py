import uuid

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


class PaymentStatusEnum(SerializableEnum):
    PENDING = 1
    FAILED = 2
    SUCCESS = 4
    TIMEOUT = 8


class Payment(TimestampMixin, db.Model):
    payment_id = db.Column(db.String, primary_key=True)
    customer_id = db.Column(db.String, db.ForeignKey('user.user_id'))
    method = db.Column(
        db.Enum(PaymentMethodEnum),
        nullable=False,
        default=PaymentMethodEnum['CARD']
    )
    total_amount = db.Column(db.Float)
    base_rate = db.Column(db.Float)
    surge_rate = db.Column(db.Float)
    tax = db.Column(db.Float)
    tip_amount = db.Column(db.Float)
    status = db.Column(db.Enum(PaymentStatusEnum))
    regulatory_charge = db.Column(db.Boolean, default=False)
    transaction_id = db.Column(db.BigInteger)
    transaction_reference = db.Column(db.String(), unique=True)
    order = db.relationship('Booking', backref='payment')
    # TODO: Add date dim


class CardAuth(BaseModelPR, TimestampMixin, db.Model):
    # TODO: add email column
    authorization_code = db.Column(db.String, unique=True)
    card_type = db.Column(db.String, index=True)
    last_four = db.Column(db.String)
    exp_month = db.Column(db.String)
    exp_year = db.Column(db.String)
    bin = db.Column(db.String)
    bank = db.Column(db.String, index=True)
    channel = db.Column(db.String)
    signature = db.Column(db.String, unique=True)
    reusable = db.Column(db.Boolean)
    country_code = db.Column(db.String)
    account_name = db.Column(db.String)
    brand = db.Column(db.String)
    user_id = db.Column(db.String, db.ForeignKey('user.user_id'))

    @classmethod
    def get_by_card_type(cls, type):
        return cls.query.filter_by(card_type=type).first()

    @classmethod
    def get_by_bank(cls, bank):
        return cls.query.filter_by(bank=bank).first()

    @classmethod
    def get_by_signature(cls, signature, session=None):
        if session:
            return cls.query.with_session(session=session).filter_by(
                signature=signature
            ).first()
        return cls.query.filter_by(signature=signature).first()


class WithdrawalAccounts(BaseModelPR, TimestampMixin, db.Model):
    __tableargs__ = db.UniqueConstraint(
        'account_number', 'user_id',
        'bank_code'
    )
    account_name = db.Column(db.String, nullable=False)
    bank_code = db.Column(db.String, nullable=False)
    account_number = db.Column(db.String, nullable=False)
    bank_name = db.Column(db.String, nullable=False)
    recipient_code = db.Column(db.String, unique=True, nullable=False)

    # foreign keys
    artisan_id = db.Column(
        db.String, db.ForeignKey('artisan.artisan_id'),
        nullable=False
    )


class Wallet(BaseModelPR, TimestampMixin, db.Model):
    balance = db.Column(db.Float, server_default="0.0")
    pin = db.Column(db.String)
    artisan_id = db.Column(
        db.String, db.ForeignKey('artisan.artisan_id'),
        nullable=False
    )


class WalletTransactionEnum(SerializableEnum):
    WITHDRAWAL = 1
    DEPOSIT = 2


class TransactionStatusEnum(SerializableEnum):
    SUCCESS = 1
    FAILED = 2
    REVERSED = 4
    DISPUTE = 8
    ERROR = 16
    PENDING = 32


class WalletTransaction(BaseModelPR, TimestampMixin, db.Model):
    wallet_id = db.Column(
        db.Integer, db.ForeignKey('wallet.id'),
        nullable=False
    )
    transaction_type = db.Column(
        db.Enum(WalletTransactionEnum),
        nullable=False,
        index=True
    )
    amount = db.Column(db.Float, nullable=False)
    transaction_id = db.Column(db.String)
    status = db.Column(db.Enum(TransactionStatusEnum))


class Withdrawals(TimestampMixin, db.Model):
    withdrawal_id = db.Column(
        db.String,
        primary_key=True,
        default=uuid.uuid4().hex
    )
    reference = db.Column(db.String, unique=True)
    transfer_code = db.Column(db.String, unique=True)
    artisan_id = db.Column(db.String, db.ForeignKey('artisan.artisan_id'))
