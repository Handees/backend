from .base import BaseModel
from datetime import datetime
from core import db
from uuid import uuid4
from geoalchemy2 import Geometry


class OrderStat:
    IN_PROGRESS = 2
    COMPLETED = 1
    CANCELLED = 0


class Order(BaseModel, db.Model):
    order_id = db.Column(db.String, default=str(uuid4))
    customer_id = db.Column(db.String, db.ForeignKey('user.user_id'))
    artisan_id = db.Column(db.String, db.ForeignKey('artisan.artisan_id'))
    start_time = db.Column(db.Date, default=datetime.utcnow())
    end_time = db.Column(db.Date)
    job_location = db.Column(Geometry(geometry_type='POINT', management=True, srid='4326'))
    status = db.Column(db.Integer)
    payment_id = db.Column(db.String, db.ForeignKey('payment.payment_id'))
    artisan_rating = db.Column(db.Integer)
    customer_rating = db.Column(db.Integer)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # TODO: set artisan_rating
        # TODO: set customer_rating
