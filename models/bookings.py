from .base import BaseModel
from datetime import datetime
from core import db
from uuid import uuid4
from geoalchemy2 import Geometry
from typing import Optional


class OrderStat:
    IN_PROGRESS = 2
    COMPLETED = 1
    CANCELLED = 0


class Booking(BaseModel, db.Model):
    booking_id = db.Column(db.String, default=str(uuid4()), primary_key=True)
    customer_id = db.Column(db.String, db.ForeignKey('user.user_id'))
    artisan_id = db.Column(db.String, db.ForeignKey('artisan.artisan_id'))
    start_time = db.Column(db.Date, default=datetime.utcnow())
    end_time = db.Column(db.Date)
    location = db.Column(Geometry(geometry_type='POINT', srid='4326'))
    status = db.Column(db.Integer)
    payment_id = db.Column(db.String, db.ForeignKey('payment.payment_id'))
    artisan_rating = db.Column(db.Integer)
    customer_rating = db.Column(db.Integer)

    def __init__(self, params: Optional[dict] = None, **kwargs):
        super().__init__(**kwargs)
        if len(kwargs.items()) <= 0:
            self.location = f"SRID=4326;POINT({params['lat']} {params['lon']})"
        else:
            self.location = f"SRID=4326;POINT({kwargs['lat']} {kwargs['lon']})"
        # TODO: set artisan_rating
        # TODO: set customer_rating
