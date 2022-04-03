from core import db
from datetime import datetime
from base import BaseModel
from uuid import uuid4


class User(BaseModel, db.Model):
    user_id = db.Column(db.String, default=str(uuid4()), primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(250))
    telephone = db.Column(db.String(100))
    password = db.Column(db.String(200))
    is_artisan = db.Column(db.Boolean, default=False)
    addresses = db.Column(db.relationship('Address'), backref='user')
    sign_up_date = db.Column(db.Date, default=datetime.utcnow())


class Artisan(BaseModel, db.Model):
    artisan_id = db.Column(db.String(200), default=str(uuid4()), primary_key=True)
    job_title = db.Column(db.String(100))
    job_description = db.Column(db.Text)
    hourly_rate = db.Column(db.Float)


class Role(BaseModel, db.Model):
    name = db.Column(db.String)
    default = db.Column(db.Boolean, default=False, index=True)
    permissions = db.Column(db.Integer)
    artisan = db.relationship('Artisan', backref='role', lazy='dynamic')
    customers = db.relationship('Customer', backref='role', lazy='dynamic')


class Permission:
    pass
