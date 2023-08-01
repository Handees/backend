from .base import BaseSQLAlchemyAutoSchema
from models.address import Address


class AddressSchema(BaseSQLAlchemyAutoSchema):
    class Meta:
        model = Address
        include_fk = True
        include_relationships = True
