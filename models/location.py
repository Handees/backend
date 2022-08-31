from .base import TimestampMixin, BaseModelPR
from core import db
from uuid import uuid4
from geoalchemy2 import Geometry


class City(TimestampMixin, BaseModelPR, db.Model):
    name = db.Column(db.String(100))
    lga = db.Column(db.String(100))
    landmarks = db.relationship('Landmark', backref='city')
    state = db.Column(db.String(80))
    country = db.Column(db.String(80))


class Landmark(TimestampMixin, db.Model):
    landmark_id = db.Column(db.String, default=str(uuid4()), primary_key=True)
    name = db.Column(db.String(150))
    lon = db.Column(db.Float)
    lat = db.Column(db.Float)
    city_id = db.Column(db.Integer, db.ForeignKey('city.id'))
    geo_cat = db.Column(Geometry(geometry_type='POINT', srid='4326'))

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.geo_cat = f'SRID=4326;POINT({self.lat} {self.lon})'
        db.session.commit()
