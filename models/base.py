from core import db


class BaseModel:
    id = db.Column(db.Integer, autoincrement=True)
