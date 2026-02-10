from models import Reviews
from .base import BaseSQLAlchemyAutoSchema


class ReviewSchema(BaseSQLAlchemyAutoSchema):
    class Meta:
        model = Reviews
