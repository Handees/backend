from datetime import datetime

from sqlalchemy.orm import column_property
from sqlalchemy import select, func, text, and_
from flask import current_app
from loguru import logger

from core import db
from models.bookings import Booking, BookingStatusEnum, BookingCategory
from models.payments import Payment
from .base import (
    TimestampMixin,
    BaseModelPR,
    SerializableEnum
)


class Permission:
    service_request = 1
    make_payments = 2
    cancel_request = 4
    service_hail = 8
    rating = 16
    admin = 32


class KYCEnum(SerializableEnum):
    UNINITIALIZED = 'UNINITIALIZED'
    IN_PROGRESS = 'IN_PROGRESS'
    COMPLETED = 'COMPLETED'


class Role(BaseModelPR, db.Model):
    name = db.Column(db.String, index=True)
    default = db.Column(db.Boolean, default=False, index=True)
    permissions = db.Column(db.Integer)
    users = db.relationship('User', backref='role', lazy='dynamic')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.permissions is None:
            self.permissions = 0

    def add_permission(self, perm):
        if not self.has_permission(perm):
            self.permissions += perm

    def has_permission(self, perm):
        return self.permissions & perm == perm

    def remove_permission(self, perm):
        if self.has_permission(perm):
            self.permissions -= perm

    def reset_permissions(self):
        self.permissions = 0

    @staticmethod
    def insert_roles():
        customer = [
            Permission.service_request,
            Permission.cancel_request,
            Permission.make_payments,
            Permission.rating
        ]
        roles = {
            'customer': customer,
            'artisan': [
                *customer,
                Permission.service_hail
            ],
            'admin': [Permission.admin]
        }
        default = 'customer'
        for r in roles:
            role = Role.query.filter_by(name=r).first()
            if not role:
                role = Role(name=r)
            role.reset_permissions()
            for perm in roles[r]:
                role.add_permission(perm)
            role.default = role.name == default
            db.session.add(role)
        db.session.commit()

    @classmethod
    def get_by_name(cls, name):
        res = cls.query.filter_by(name=name).first()
        return res

    @staticmethod
    def updateRolePermissions(role_name, perm_val):
        role: Role = Role.query.filter_by(name=role_name).first()
        role.add_permission(perm_val)
        try:
            db.session.commit()
        except Exception as e:
            logger.exception(e)
            db.session.rollback()
        finally:
            db.session.close()


class User(TimestampMixin, db.Model):
    id = db.Column(
        db.Integer,
        nullable=False,
        unique=True,
        autoincrement=True,
        server_default=text("nextval('user_id_seq')")
    )
    user_id = db.Column(db.String, primary_key=True, unique=True)
    first_name = db.Column(db.String(50))
    last_name = db.Column(db.String(50))
    telephone = db.Column(db.String(100))
    email = db.Column(db.String(100), unique=True, index=True)
    is_artisan = db.Column(db.Boolean, default=False)
    is_email_verified = db.Column(db.Boolean, default=False)
    address = db.Column(db.String(500))
    sign_up_date = db.Column(db.Date, default=datetime.utcnow())
    profile_picture = db.Column(db.String())
    mobile_app_registration_token = db.Column(db.String())
    no_of_bookings = db.Column(db.Integer, server_default=text('0'))
    no_of_ratings = db.Column(db.Integer, server_default=text('0'))
    ratings_weighted_sum = db.Column(db.Integer, server_default=text('0'))

    # relationships
    artisan_profile = db.relationship(
        'Artisan',
        backref='user_profile',
        uselist=False
    )
    reviews = db.relationship('Reviews', backref='user', foreign_keys='Reviews.user_id')
    bookings = db.relationship('Booking', backref='user', lazy='dynamic')
    role_id = db.Column(db.Integer, db.ForeignKey('role.id'), nullable=False)
    cards = db.relationship('CardAuth', backref='user')
    payments = db.relationship('Payment', backref='user')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.role is None:
            if self.email == current_app.config['ADMIN_EMAIL']:
                self.role = Role.query.filter_by(name='Admin').first()
            else:
                self.role = Role.query.filter_by(default=True).first()

    def can(self, perm):
        return self.role and self.role.has_permission(perm)

    def is_admin(self):
        return self.can(Permission.admin)

    def is_verified(self):
        pass

    def upgrade_to_artisan(self):
        self.role = Role.query.filter_by(name='artisan').first()

    def can_artisan(self):
        return self.can(Permission.service_hail)

    @classmethod
    def get_by_email(cls, email, session=None):
        if session:
            return cls.query.with_session(
                session=session
            ).filter_by(email=email).first()
        return cls.query.filter_by(email=email).first()
    
    @classmethod
    def get_by_id(cls, uid, session=None):
        if session:
            return cls.query.with_session(
                session=session
            ).filter_by(user_id=uid).first()
        return cls.query.filter_by(user_id=uid).first()

    @property
    def average_rating_score(self):
        if not self.no_of_ratings:
            return 0
        return self.ratings_weighted_sum / self.no_of_ratings

    def get_star_rating(self, c=3.75):
        m = 5.0
        r = self.average_rating_score
        v = self.no_of_ratings
        rating = ((v/(v+m))*r) + ((m/(v+m))*c)
        return round(rating, 2)

    def calculate_dynamic_request_ttl(self, c=3.75):
        """
            Calculates how long a booking request stays alive in Redis
            based on the customer's star rating.
        """
        rating = self.get_star_rating(c)
        BASE_SECONDS = 60
        BONUS_PER_STAR = 40
        ttl = BASE_SECONDS + (rating * BONUS_PER_STAR)
        return int(ttl)

    @classmethod
    def fetch_active_bookings(cls, user_id, session):
        subq = (
            select(
                Booking.booking_id, Booking.status, Booking.created_at,
                cls.first_name, cls.last_name, cls.profile_picture,
                Booking.settlement_type, Artisan.artisan_id,
                BookingCategory.name, cls.telephone
            )
            .join(Artisan, Booking.artisan_id == Artisan.artisan_id)
            .join(cls, Artisan.user_id == cls.user_id)
            .join(BookingCategory, BookingCategory.id == Booking.category_id)
            .where(
                and_(
                    Booking.status == BookingStatusEnum.IN_PROGRESS,
                    Booking.customer_id == user_id
                )
            )
        ).subquery()
        stmt = (
            select(
                func.json_agg(
                    func.json_build_object(
                        'matched_artisan', func.jsonb_build_object(
                            'name', func.concat_ws(' ', subq.c.first_name, subq.c.last_name),
                            'settlement_type', subq.c.settlement_type,
                            'id', subq.c.artisan_id,
                            'profile_picture', subq.c.profile_picture,
                            'phone_number', subq.c.telephone
                        ),
                        'id', subq.c.booking_id, 'status', subq.c.status,
                        'category', subq.c.name,
                        'created_at', subq.c.created_at
                    )
                )
            )
        ).select_from(subq)
        return session.execute(stmt).scalar()



# @event.listens_for(User, 'before_update')
# def before_update_listener(mapper, connection, target):
#     # Check if the 'profile_picture' field is being updated
#     from sqlalchemy.orm import inspect
#     inspector = inspect(target)

#     if inspector.attrs.profile_picture.history.has_changes():
#         # Get the old and new email values
#         old_email = inspector.attrs.email.history.deleted[0]
#         new_email = inspector.attrs.email.history.added[0]

#         print(f"Original email: {old_email}")
#         print(f"New email: {new_email}")

#         # Modify the value directly on the target object
#         target.email = f"modified_{new_email}"
#         print(f"Modified email before commit: {target.email}")


class Artisan(TimestampMixin, db.Model):
    artisan_id = db.Column(db.String(200), primary_key=True)
    is_verified = db.Column(db.Boolean, default=False)
    job_title = db.Column(db.String(100))
    jobs_completed = db.Column(db.Integer, default=0, server_default=text('0'))
    sign_up_date = db.Column(db.Date, default=datetime.utcnow())
    hourly_rate = db.Column(db.Float)
    kyc_status = db.Column(
        db.Enum(KYCEnum),
        nullable=False,
        default=KYCEnum.UNINITIALIZED
    )
    no_of_ratings = db.Column(db.Integer, server_default=text('0'))
    ratings_weighted_sum = db.Column(db.Integer, server_default=text('0'))

    # relationships and f_keys
    reviews = db.relationship('Reviews', backref='artisan')
    bank_accounts = db.relationship('WithdrawalAccounts', backref='artisan')
    user_id = db.Column(db.String, db.ForeignKey('user.user_id'))
    job_category_id = db.Column(
        db.Integer,
        db.ForeignKey('bookingcategory.id')
    )
    bookings = db.relationship(
        'Booking', backref='artisan', foreign_keys='Booking.artisan_id'
    )
    kyc_attempts = db.relationship('Kyc', backref='artisan')
    wallet = db.relationship('Wallet', backref='artisan', uselist=False)
    current_booking_id = db.Column(db.String, db.ForeignKey('booking.booking_id'))
    current_booking = db.relationship(
        'Booking',
        foreign_keys=[current_booking_id],
        post_update=True  # CRITICAL: Tells SQLAlchemy to handle the cyclic insert/update safely
    )


    # add-ons
    jobs_assigned = column_property(
        select(func.count(Booking.booking_id))
        .where(Booking.artisan_id == artisan_id)
        .correlate_except(Booking)
        .scalar_subquery()
    )
    total_earnings = column_property(
        select(
            func.coalesce(func.sum(Payment.total_amount), 0)
        )
        .select_from(Booking)
        .join(Payment, Booking.payment_id == Payment.payment_id)
        .where(
            Booking.artisan_id == artisan_id,
            Booking.status == BookingStatusEnum.COMPLETED
        )
        .correlate_except(Booking, Payment)
        .scalar_subquery()
    )

    @property
    def average_rating_score(self):
        if not self.no_of_ratings:
            return 0
        return self.ratings_weighted_sum / self.no_of_ratings

    def get_star_rating(self, c=3.75):
        m = 5.0
        r = self.average_rating_score
        v = self.no_of_ratings
        rating = ((v/(v+m))*r) + ((m/(v+m))*c)
        return round(rating, 2)

    def update_completed_job_count(self):
        """ increase the no of job completed by unit value """
        self.jobs_completed += 1

    def is_assigned_to_booking(self, booking_id):
        return self.booking.booking_id == booking_id

    @classmethod
    def get_by_user_id(cls, user_id):
        return cls.query.filter_by(user_id=user_id).first()

    @property
    def activity(self):
        return {
            'completed': self.jobs_completed,
            'incomplete': self.jobs_assigned - self.jobs_completed,
            'completed_percentage': round(
                (self.jobs_completed / self.jobs_assigned),
                2
            ) * 100.0
        }

    # def get_active_booking(self):
    #     pass

class Kyc(TimestampMixin, db.Model):
    kyc_id = db.Column(db.String(200), primary_key=True)
    kyc_type = db.Column(db.String)
    drivers_license_number = db.Column(db.String(11))
    nin_number = db.Column(db.String(11))
    date_of_birth = db.Column(db.Date)
    last_name = db.Column(db.String)
    passport_number = db.Column(db.String(10))
    image = db.Column(db.String)
    artisan_id = db.Column(db.ForeignKey('artisan.artisan_id'))
