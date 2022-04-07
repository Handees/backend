from .base import BaseModel
from core import db
from uuid import uuid4


class Payment(BaseModel, db.Model):
    payment_id = db.Column(db.String, default=str(uuid4()), primary_key=True)
    customer_id = db.Column(db.String, db.ForeignKey('user.user_id'))
    method = db.Column(db.String(50))
    total_amount = db.Column(db.Float)
    base_rate = db.Column(db.Float)
    surge_rate = db.Column(db.Float)
    tax = db.Column(db.Float)
    tip_amount = db.Column(db.Float)
    status = db.Column(db.Boolean, default=False)
    transaction_id = db.Column(db.String)
    order = db.relationship('Order', backref='payment')
    # TODO: Add date dim