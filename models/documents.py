import os
from uuid import uuid4
from datetime import datetime

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
    blob_id = db.Column(db.String, primary_key=True)
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
        return generate_presigned_url(
            bucket_name=os.getenv('BUCKET_NAME'),
            object_name=self.filename,
            action='upload'
        )

    @property
    def download_url(self):
        from utils import generate_presigned_url
        return generate_presigned_url(
            bucket_name=os.getenv('BUCKET_NAME'),
            object_name=self.filename,
            action='download'
        )
