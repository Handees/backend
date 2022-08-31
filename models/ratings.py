from core import db
from .base import BaseModelPR, TimestampMixin


class Rating(TimestampMixin, BaseModelPR, db.Model):
    weight = db.Column(db.Integer, default=0)
    comment = db.Column(db.Text)
    user_id = db.Column(db.String, db.ForeignKey('user.user_id'))
    artisan_id = db.Column(db.String, db.ForeignKey('artisan.artisan_id'))

    @property
    def rating(self):
        pass

    @rating.setter
    def rating():
        pass
