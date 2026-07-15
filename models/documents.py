import os
from uuid import uuid4
from datetime import datetime
from sqlalchemy import select, and_

from sqlalchemy import UniqueConstraint

import utils
from core import db
from .base import TimestampMixin, BaseModelPR, SerializableEnum


class BlobTypes(SerializableEnum):
    USER_PROFILE = 1
    ARTISAN_PROFILE = 2
    USER_KYC = 4
    ARTISAN_KYC = 8
    BOOKING = 16


class Document(TimestampMixin, db.Model):
    doc_id = db.Column(db.String, default=str(uuid4()), primary_key=True)
    name = db.Column(db.String(20))
    doc_type = db.Column(db.String(50))
    state = db.Column(db.String(50))
    expiry_date = db.Column(db.Date)
    country = db.Column(db.String(60))
    date_verified = db.Column(db.Date)
    is_verified = db.Column(db.Boolean, default=False)
    date_uploaded = db.Column(db.Date, default=datetime.utcnow())
    artisan_id = db.Column(db.String, db.ForeignKey('artisan.artisan_id'))
    category_id = db.Column(db.Integer, db.ForeignKey('document_category.id'))


class Document_category(TimestampMixin, BaseModelPR, db.Model):
    name = db.Column(db.String(50))
    documents = db.relationship('Document', backref='category')

    @staticmethod
    def insert_categories():
        pass


class Blob(TimestampMixin, db.Model):
    blob_id = db.Column(db.String, primary_key=True, default=lambda: uuid4().hex)
    filename = db.Column(db.String, nullable=False, index=True)
    content_type = db.Column(db.String, nullable=False, index=True)
    url = db.Column(db.String)
    blob_type = db.Column(db.Enum(BlobTypes), nullable=False, index=True)
    user_id = db.Column(
        db.String,
        db.ForeignKey('user.user_id'),
        index=True,
        nullable=False
    )
    booking_id = db.Column(
        db.String,
        db.ForeignKey('booking.booking_id'),
        index=True
    )

    @property
    def upload_url(self):
        from utils import generate_presigned_url
        storage_path = f"uploads/{self.user_id}/{self.blob_id}"
        return generate_presigned_url(
            bucket_name=os.getenv('BUCKET_NAME'),
            object_name=storage_path,
            action='upload',
            content_type=self.content_type,
            filename=self.filename
        )

    @property
    def download_url(self):
        from utils import generate_presigned_url
        storage_path = f"uploads/{self.user_id}/{self.blob_id}"
        return generate_presigned_url(
            bucket_name=os.getenv('BUCKET_NAME'),
            object_name=storage_path,
            action='download',
            content_type=self.content_type,
            filename=self.filename
        )

    @classmethod
    def get_by_id(cls, id, session=None):
        if session:
            stmt = select(cls).where(
                cls.blob_id == id
            )
            return session.scalar(stmt)
    
    @classmethod
    def get_user_profile_blob(cls, user_id, session=None):
        if session:
            stmt = select(cls).where(
                and_(
                    cls.user_id == user_id,
                    cls.blob_type == BlobTypes.USER_PROFILE
                )
            )
            return session.scalar(stmt)
