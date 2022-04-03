from core import db
from uuid import uuid4
from datetime import datetime
from .base import BaseModel, BaseModelPR


class Document(BaseModel, db.Model):
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


class Document_category(BaseModelPR, db.Model):
    name = db.Column(db.String(50))
    documents = db.relationship('Document', backref='category')

    @staticmethod
    def insert_categories():
        pass
