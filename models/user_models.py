from core import db
from flask import current_app
from datetime import datetime
from .base import TimestampMixin, BaseModelPR


class Permission:
    service_request = 1
    cancel_request = 2
    service_hail = 4
    rating = 8
    admin = 12


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
        roles = {
            'customer': [
                Permission.service_request,
                Permission.cancel_request,
                Permission.rating
            ],
            'artisan': [
                Permission.service_request,
                Permission.cancel_request,
                Permission.rating,
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


class User(TimestampMixin, db.Model):
    user_id = db.Column(db.String, primary_key=True, unique=True)
    name = db.Column(db.String(100))
    telephone = db.Column(db.String(100))
    email = db.Column(db.String(100), unique=True, index=True)
    is_artisan = db.Column(db.Boolean, default=False)
    is_email_verified = db.Column(db.Boolean, default=False)
    addresses = db.relationship('Address', backref='user')
    sign_up_date = db.Column(db.Date, default=datetime.utcnow())
    artisan_profile = db.relationship('Artisan', backref='user_profile', uselist=False)
    ratings = db.relationship('Rating', backref='user')
    bookings = db.relationship('Booking', backref='user', lazy='dynamic')
    role_id = db.Column(db.Integer, db.ForeignKey('role.id'))
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
    def get_by_email(cls, email):
        return cls.query.filter_by(email=email).first()


class Artisan(TimestampMixin, db.Model):
    artisan_id = db.Column(db.String(200), primary_key=True)
    is_verified = db.Column(db.Boolean, default=False)
    job_title = db.Column(db.String(100))
    jobs_completed = db.Column(db.Integer, default=0)
    sign_up_date = db.Column(db.Date, default=datetime.utcnow())
    hourly_rate = db.Column(db.Float)

    # relationships and f_keys
    ratings = db.relationship('Rating', backref='artisan')
    user_id = db.Column(db.String, db.ForeignKey('user.user_id'))
    job_category_id = db.Column(db.Integer, db.ForeignKey('bookingcategory.id'))
    booking = db.relationship('Booking', backref='artisan', uselist=False)

    @property
    def bookings(self):
        from models import Booking
        return Booking.query.filter_by(artisan_id=self.artisan_id)

    def update_completed_job_count(self):
        """ increase the no of job completed by unit value """
        self.jobs_completed += 1

    def is_assigned_to_booking(self, booking_id):
        return self.booking.booking_id == booking_id
