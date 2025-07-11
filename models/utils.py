from core import db
from .base import BaseModelPR


# class Room(BaseModelPR, db.Model):
#     name = db.Column(db.String)
#     client_sid


class Socket(BaseModelPR, db.Model):
    sid = db.Column(db.String, unique=True, nullable=False)
