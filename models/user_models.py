from core import db
from flask import current_app
from datetime import datetime
from .base import BaseModel, BaseModelPR
from uuid import uuid4


class Permission:
    service_request = 1
    cancel_request = 2
    service_hail = 4
    rating = 8
    admin = 12


class Role(BaseModelPR, db.Model):
    name = db.Column(db.String)
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
            'artisan': [Permission.service_hail],
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


class User(BaseModel, db.Model):
    user_id = db.Column(db.String, default=str(uuid4()), primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(250))
    telephone = db.Column(db.String(100))
    password = db.Column(db.String(200))
    is_artisan = db.Column(db.Boolean, default=False)
    is_email_verified = db.Column(db.Boolean, default=False)
    addresses = db.relationship('Address', backref='user')
    sign_up_date = db.Column(db.Date, default=datetime.utcnow())
    artisan_profile = db.relationship('Artisan', backref='user_profile', uselist=False)
    role_id = db.Column(db.Integer, db.ForeignKey('role.id'))

    def __init__(self, **kwargs):
        super().__init__(kwargs)
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


class Artisan(BaseModel, db.Model):
    artisan_id = db.Column(db.String(200), default=str(uuid4()), primary_key=True)
    job_title = db.Column(db.String(100))
    job_description = db.Column(db.Text)
    hourly_rate = db.Column(db.Float)
    sign_up_date = db.Column(db.Date, default=datetime.utcnow())
    user_id = db.Column(db.String, db.ForeignKey('user.user_id'))

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.user_profile = kwargs['user']
