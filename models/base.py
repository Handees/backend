from core import db
from datetime import datetime
import enum


class TimestampMixin(object):
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)

    def load_from_param_or_kwargs(self, params, **kwargs):
        if params:
            for k, v in params.items():
                if hasattr(self, k):
                    setattr(self, k, v)
                else:
                    return False
        if kwargs.items():
            for k, v in params.items():
                if hasattr(self, k):
                    setattr(self, k, v)
                else:
                    return False
        return True


class BaseModelPR(object):
    id = db.Column(db.Integer, autoincrement=True, primary_key=True)


class SerializableEnum(str, enum.Enum):
    """JSON Serializable enums for easy response generation.
    Note: sub-classing str makes it serializable. see: https://stackoverflow.com/a/51976841/2528464
    """

    pass
