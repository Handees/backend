from core import db
from datetime import datetime
from base import BaseModel
from uuid import uuid4


class AddressTypes(BaseModel, db.Model):
    type_id = db.Column(db.String, default=str(uuid4()), primary_key=True)
    name = db.Column(db.String(15))
    description = db.Column(db.String(50))
    active = db.Column(db.Boolean)
    last_update_time = db.Column(db.Date)
    addresses = db.relationship('Address', backref='address_type')


class Address(BaseModel, db.Model):
    address_id = db.Column(db.String, default=str(uuid4()), primary_key=True)
    address_line_1 = db.Column(db.String(50), nullable=False)
    address_line_2 = db.Column(db.String(50))
    state_or_province = db.Column(db.String(50))
    postal_code = db.Column(db.String(6))
    last_update_time = db.Column(db.Date, default=datetime.utcnow())
    user_id = db.Column(db.String, db.ForeignKey('user.user_id'))
    address_type_id = db.Column(db.String, db.ForeignKey('addresstypes.type_id'))
