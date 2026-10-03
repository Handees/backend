import os
import uuid

import datetime
from sqlalchemy import select, and_, func
from sqlalchemy.orm import column_property
from dotenv import load_dotenv
from geoalchemy2 import Geometry
from datetime import datetime as dt

from .base import (
    TimestampMixin,
    BaseModelPR,
    SerializableEnum
)
from core import db
from core.exc import InvalidBookingCategory, BookingLimitExceeded, BookingHasContract
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
    booking_id = db.Column(
        db.String,
        db.ForeignKey('booking.booking_id'),
        nullable=False
    )
    name = db.Column(db.Enum(BookingWorkDayEnum), nullable=False)
    date = db.Column(db.Date)
    work_sessions = db.relationship(
        'BookingWorkSession',
        backref='booking_work_day'
    )


class BookingWorkSession(BaseModelPR, TimestampMixin, db.Model):
    working_day_id = db.Column(
        db.Integer,
        db.ForeignKey('booking_workday.id'),
        nullable=False
    )
    booking_id = db.Column(
        db.String,
        db.ForeignKey('booking.booking_id'),
        nullable=False
    )
    clock_in = db.Column(db.DateTime)
    clock_out = db.Column(db.DateTime)


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

    @classmethod
    def setup_booking_contract(cls, sess, booking, duration, duration_unit):
        """
        Helper to attach contract details to a booking after it has been matched/verified.
        """
        # Ensure the unit is a valid Enum
        if isinstance(duration_unit, str):
            try:
                duration_unit = BookingContractDurationEnum[duration_unit.upper()]
            except KeyError:
                raise ValueError(f"Invalid duration unit: {duration_unit}")

        if booking.booking_contract:
            raise BookingHasContract(
                f"This booking {booking.booking_id} already has a booking-contract associated with it"
            )

        # Flag the parent booking as a contract
        booking.contract_type = True

        new_contract = cls(
            duration=duration,
            duration_unit=duration_unit
        )
        booking.booking_contract = new_contract

        sess.add(new_contract)
        sess.flush()
        
        return new_contract


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
    request_location = db.Column(db.String())
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
    clock_in_flag = db.Column(
        db.Boolean, server_default='false',
        default=False
    )
    booking_contract = db.relationship(
        'BookingContract',
        backref='booking',
        uselist=False
    )
    current_work_session_id = db.Column(
        db.Integer,
        db.ForeignKey('booking_work_session.id')
    )
    customer_address = db.Column(db.String)
    images = db.relationship('Blob', backref='booking')
    working_days = db.relationship('BookingWorkDay', backref='booking')
    chat = db.relationship('Chat', uselist=False, backref='booking')

    lat = column_property(func.ST_Y(location))
    lon = column_property(func.ST_X(location))

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
        clock = BookingWorkSession(
            working_day_id=new_work_day.id,
            clock_in=current_day,
            booking_id=self.booking_id
        )
        sess.add(clock)
        sess.flush()
        self.current_work_session_id = clock.id

    @classmethod
    def create_booking(cls, sess, new_order, data, user):
        from models.user_models import User

        MAX_ACTIVE_BOOKINGS = 3
        customer_id = user.user_id
        sess.execute(
            select(User.user_id)
            .where(User.user_id == customer_id)
            .with_for_update()
        )
        active_count = sess.execute(
            select(func.count()).select_from(Booking).where(
                and_(
                    Booking.customer_id == customer_id,
                    Booking.status == BookingStatusEnum.IN_PROGRESS,
                )
            )
        ).scalar()
        if active_count >= MAX_ACTIVE_BOOKINGS:
            error_msg = "Booking Limit Exceeded; Can't Have more than 3 active requests"
            sess.rollback()
            raise BookingLimitExceeded(error_msg)

        new_order.booking_id = uuid.uuid4().hex
        new_order.status = BookingStatusEnum.PENDING
        category = BookingCategory.get_by_name(data['job_category'])
        if not category:
            sess.rollback()
            error_msg = "category with name '{}' not found"
            raise InvalidBookingCategory(error_msg.format(data['category']))

        new_order.booking_category = category
        new_order.user = user
        sess.add(new_order)
        sess.flush()
        return new_order

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
                date=current_day.date(),
                booking_id=self.booking_id
            )
            if self.contract_type:
                working_day.contract_id = self.booking_contract.id
            sess.add(working_day)
            sess.flush()

        # add clock-in
        if clock_in:
            clock = BookingWorkSession(
                working_day_id=working_day.id,
                booking_id=self.booking_id,
                clock_in=current_day
            )
            sess.add(clock)
            sess.flush()
            self.current_work_session_id = clock.id
        else:
            self.current_work_session(sess).clock_out = current_day

        sess.flush()

    def current_work_session(self, sess):
        return sess.scalar(
            select(BookingWorkSession).where(
                BookingWorkSession.id == self.current_work_session_id
            )
        )

    @classmethod
    def fetch_user_bookings(cls, user_id):
        return select(cls).where(
            cls.customer_id == user_id
        )
