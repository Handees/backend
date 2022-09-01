from .base import TimestampMixin, BaseModelPR, SerializableEnum
from datetime import datetime
from core import db
from geoalchemy2 import Geometry
# from typing import Optional


categories = [
    'laundry',
    'carpentary',
    'hair styling',
    'clothing',
    'plumbing',
    'automobile',
    'generator repair',
    'tv cable engineer',
    'weldering',
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


class BookingContract(TimestampMixin, BaseModelPR, db.Model):
    booking_id = db.Column(db.String, db.ForeignKey('booking.booking_id'))
    start_time = db.Column(db.Date)
    end_time = db.Column(db.Date)
    agreed_start_time = db.Column(db.Date)
    agreed_end_time = db.Column(db.Date)


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
    _contract_type = db.Column("contract_type", db.Boolean, default=False)
    artisan_rating = db.Column(db.Integer)
    customer_rating = db.Column(db.Integer)
    settlement_type = db.Column(db.Enum(
        SettlementEnum
    ), nullable=False)
    date_of_booking = db.Column(db.Date, default=datetime.utcnow())

    def update_start_time(self):
        self.start_time = datetime.utcnow()

    def update_end_time(self):
        self.end_time = datetime.utcnow()

    # TODO: set artisan_rating
    # TODO: set customer_rating

    def update_status(self, status_code):
        self.status = BookingStatusEnum(status_code)

    @property
    def contract_type(self):
        return self._contract_type

    @contract_type.setter
    def contract_type(self, status, contract_details):
        if status is True:
            # create booking contract object
            self._contract_type = True
            new_contract = BookingContract().load_from_param_or_kwargs(
                params=contract_details
            )
            db.session.add(new_contract)
            db.session.commit()
