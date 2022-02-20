from core import db
from datetime import datetime
from uuid import uuid4


class BaseModel(db.Model):
    id = db.Column(db.Integer, primary_key=True, unique=True, nullable=False)


class User(BaseModel):
    name = db.Column(db.String(100))
    email = db.Column(db.String(250))
    telephone = db.Column(db.String(100))
    password = db.Column(db.String(200))
    sign_up_date = db.Column(db.Date, default=datetime.utcnow())


class Artisan(User):
    artisan_id = db.Column(db.String(200), default=str(uuid4()))
    job_title = db.Column(db.String(100))
    job_description = db.Column(db.Text)
    hourly_rate = db.Column(db.Float)

class Customer(User):
    customer_id = db.Column(db.String(200), default=str(uuid4()))
    home_address = db.Column(db.Text)


class Role(BaseModel):
    pass


class Permission:
    pass