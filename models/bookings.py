import os

import datetime
from sqlalchemy import select, and_
from dotenv import load_dotenv
from geoalchemy2 import Geometry
from datetime import datetime as dt

from .base import (
    TimestampMixin,
    BaseModelPR,
    SerializableEnum
)
from core import db
# from typing import Optional

load_dotenv()

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
    PENDING = 1
    ARTISAN_MATCHED = 2
    ARTISAN_ARRIVED = 4
    IN_PROGRESS = 8
    COMPLETED = 16
    ARTISAN_CANCELLED = 32
    CUSTOMER_CANCELLED = 64


class SettlementEnum(SerializableEnum):
    NEGOTIATION = 2
    HOURLY_RATE = 1


class BookingContractDurationEnum(SerializableEnum):
    DAYS = 1
    WEEKS = 2


class BookingPaymentMethod(SerializableEnum):
    CASH = 1
    CARD = 2


class BookingWorkDayEnum(SerializableEnum):
    MONDAY = 1
    TUESDAY = 2
    WEDNESDAY = 4
    THURSDAY = 8
    FRIDAY = 16
    SATURDAY = 32
    SUNDAY = 64


class BookingClockEventTypeEnum(SerializableEnum):
    CLOCK_IN = 1
    CLOCK_OUT = 2


class BookingWorkDay(BaseModelPR, TimestampMixin, db.Model):
    __tablename__ = 'booking_workday'
    contract_id = db.Column(
        db.Integer(),
        db.ForeignKey('booking_contract.id'),
        nullable=True
    )
    booking_id = db.Column(db.String, db.ForeignKey('booking.booking_id'))
    name = db.Column(db.Enum(BookingWorkDayEnum), nullable=False)
    date = db.Column(db.Date)


class BookingClockEvent(BaseModelPR, TimestampMixin, db.Model):
    working_day_id = db.Column(
        db.Integer,
        db.ForeignKey('booking_workday.id'),
        nullable=False
    )
    event_type = db.Column(db.Enum(BookingClockEventTypeEnum), nullable=False)


class BookingContract(TimestampMixin, BaseModelPR, db.Model):
    booking_id = db.Column(db.String, db.ForeignKey('booking.booking_id'))
    start_time = db.Column(
        db.Date,
        nullable=False,
        default=dt.now(datetime.timezone.utc)
    )
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
    artisans = db.relationship('Artisan', backref='booking_category')

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
    customer_id = db.Column(
        db.String, db.ForeignKey('user.user_id'),
        index=True
    )
    category_id = db.Column(
        db.Integer, db.ForeignKey('bookingcategory.id'),
        index=True
    )
    artisan_id = db.Column(
        db.String, db.ForeignKey('artisan.artisan_id'),
        index=True
    )
    start_time = db.Column(db.Date)
    end_time = db.Column(db.Date)
    location = db.Column(Geometry(geometry_type='POINT', srid='4326'))
    description = db.Column(db.Text())
    status = db.Column(db.Enum(BookingStatusEnum))
    payment_id = db.Column(db.String, db.ForeignKey('payment.payment_id'))
    contract_type = db.Column(
        "contract_type",
        db.Boolean,
        default=False,
        index=True
    )
    artisan_rating = db.Column(db.Integer)
    customer_rating = db.Column(db.Integer)
    settlement_type = db.Column(
        db.Enum(
            SettlementEnum
        ), nullable=True,
        index=True
    )
    details_confirmed = db.Column(db.Boolean, default=False)
    payment_method = db.Column(
        db.Enum(BookingPaymentMethod),
        index=True
    )
    booking_contract = db.relationship(
        'BookingContract',
        backref='booking',
        uselist=False
    )
    images = db.relationship('Blob', backref='booking')

    def update_start_time(self):
        self.start_time = dt.utcnow()

    def update_end_time(self):
        self.end_time = dt.utcnow()

    # TODO: set artisan_rating
    # TODO: set customer_rating

    def update_status(self, enum):
        self.status = enum

    def fetch_hourly_pay(self):
        res = None
        if self.settlement_type == SettlementEnum.HOURLY_RATE:
            time_spent = round(
                (self.end_time - self.start_time).total_seconds(),
                5
            )
            hrs_spent = time_spent / 3600
            res = self.artisan.hourly_rate * hrs_spent

        return res

    def start_booking(self, sess):
        self.status = BookingStatusEnum.IN_PROGRESS
        current_day = dt.now(datetime.timezone.utc)
        dow = current_day.strftime("%A")
        new_work_day = BookingWorkDay(
            name=BookingWorkDayEnum[dow.upper()],
            date=current_day.date()
        )
        if self.contract_type:
            contract = self.booking_contract
            new_work_day.contract_id = contract.id

        sess.add(new_work_day)
        sess.flush()
        clock_in = BookingClockEvent(
            working_day_id=new_work_day.id,
            event_type=BookingClockEventTypeEnum.CLOCK_IN
        )
        sess.add(clock_in)
        sess.flush()

    def add_clock_event(self, sess, clock_in=True):
        current_day = dt.now(datetime.timezone.utc)
        dow = current_day.strftime("%A")
        # find if working day already exists
        stmt = select(BookingWorkDay).where(
            and_(
                BookingWorkDay.date == current_day.date(),
                BookingWorkDay.booking_id == self.booking_id
            )
        )
        working_day = sess.scalar(stmt)
        if not working_day:
            working_day = BookingWorkDay(
                name=BookingWorkDayEnum[dow.upper()],
                date=current_day.date()
            )
            if self.contract_type:
                working_day.contract_id = self.booking_contract.id
            sess.flush()
        # add clock-in
        clock_in = BookingClockEvent(
            working_day_id=working_day.id
        )
        if clock_in:
            clock_in.event_type = BookingClockEventTypeEnum.CLOCK_IN
        else:
            clock_in.event_type = BookingClockEventTypeEnum.CLOCK_OUT

        sess.add(clock_in)
        sess.flush()
