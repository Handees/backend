from .base import (
    TimestampMixin,
    BaseModelPR,
    SerializableEnum
)
from core import db

from datetime import datetime as dt
from geoalchemy2 import Geometry
# from typing import Optional


categories = [
    'laundry',
    'carpentry',
    'hair styling',
    'clothing',
    'plumbing',
    'automobile',
    'generator repair',
    'tv cable engineer',
    'welding',
    'gardening',
    'house keeping'
]


class BookingStatusEnum(SerializableEnum):
    IN_PROGRESS = 8
    COMPLETED = 4
    CANCELLED = 2
    ARTISAN_ARRIVED = 1


class SettlementEnum(SerializableEnum):
    NEGOTIATION = 2
    HOURLY_RATE = 1


class BookingContractDurationEnum(SerializableEnum):
    DAYS = 1
    WEEKS = 2


class BookingContract(TimestampMixin, BaseModelPR, db.Model):
    booking_id = db.Column(db.String, db.ForeignKey('booking.booking_id'))
    start_time = db.Column(db.Date, nullable=False, default=dt.utcnow())
    end_time = db.Column(db.Date)
    duration = db.Column(db.Integer, nullable=False)
    duration_unit = db.Column(db.Enum(
        BookingContractDurationEnum
    ), nullable=False)

    def update_start_time(self):
        self.start_time = dt.utcnow()

    def update_end_time(self):
        self.end_time = dt.utcnow()


class BookingCategory(BaseModelPR, db.Model):
    __tablename__ = 'bookingcategory'
    name = db.Column(db.String(150), unique=True, nullable=False, index=True)
    bookings = db.relationship('Booking', backref='booking_category')
    artisan = db.relationship('Artisan', backref='booking_category')

    @classmethod
    def create_categories(cls):
        for cat in categories:
            # check if category exists
            if cls.query.filter_by(name=cat).first():
                continue
            new_category = cls(name=cat)

            db.session.add(new_category)
        db.session.commit()

    @classmethod
    def verify_category(name):
        # TODO: make more clever
        if name.strip(" ").lower() in categories.keys():
            return True
        return False

    @classmethod
    def get_by_name(cls, val):
        return cls.query.filter_by(name=val).first()

    @property
    def artisans(self):
        return self.artisan


class Booking(TimestampMixin, db.Model):
    # TODO: Implement activity track/logs

    # Table Columns
    booking_id = db.Column(db.String, primary_key=True, unique=True)
    customer_id = db.Column(db.String, db.ForeignKey('user.user_id'))
    category_id = db.Column(db.Integer, db.ForeignKey('bookingcategory.id'))
    artisan_id = db.Column(db.String, db.ForeignKey('artisan.artisan_id'))
    start_time = db.Column(db.Date)
    end_time = db.Column(db.Date)
    location = db.Column(Geometry(geometry_type='POINT', srid='4326'))
    status = db.Column(db.Enum(BookingStatusEnum))
    payment_id = db.Column(db.String, db.ForeignKey('payment.payment_id'))
    contract_type = db.Column("contract_type", db.Boolean, default=False)
    artisan_rating = db.Column(db.Integer)
    customer_rating = db.Column(db.Integer)
    settlement_type = db.Column(db.Enum(
        SettlementEnum
    ), nullable=True)
    details_confirmed = db.Column(db.Boolean, default=False)
    date_of_booking = db.Column(db.Date, default=dt.utcnow())
    booking_contract = db.relationship('BookingContract', backref='booking', uselist=False)

    def update_start_time(self):
        self.start_time = dt.utcnow()

    def update_end_time(self):
        self.end_time = dt.utcnow()

    # TODO: set artisan_rating
    # TODO: set customer_rating

    def update_status(self, status_code):
        self.status = BookingStatusEnum(status_code)

    def fetch_hourly_pay(self):
        res = None
        if self.settlement_type == SettlementEnum('1'):
            time_spent = round(
                (self.end_time - self.start_time).total_seconds(),
                5
            )
            hrs_spent = time_spent / 3600
            res = self.artisan.hourly_rate * hrs_spent

        return res
