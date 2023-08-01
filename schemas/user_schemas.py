from models.user_models import User
from .artisan import ArtisanSchema
from .base import (
    BaseSQLAlchemyAutoSchema,
    BaseSchema
)
from core import ma
from marshmallow import fields
from . import CardAuthSchema


class UserSchema(BaseSQLAlchemyAutoSchema):
    class Meta:
        model = User
        include_fk = True
        include_relationships = True
        exclude = (
            'role',
            'role_id',
            'updated_at',
            'bookings',
            'payments'
        )

    artisan_profile = fields.Nested(
        ArtisanSchema(exclude=(
            'user_id', 'user_profile',
        ))
    )
    cards = fields.Nested(CardAuthSchema, many=True)
    addresses = fields.Nested("AddressSchema", exclude=(
        'user_id', 'user'
    ))
    # load_instance = True
    # transient = True

    # # read only
    # dump_only = (
    #     'created_at',
    # )

    # @post_dump
    # def edit_dump(self, data, *args, **kwargs):
    #     if not data['artisan_profile']:
    #         data['artisan_profile'] = None
    #     return data


class AddNewUserSchema(BaseSchema):
    user_id = ma.String(required=True)
    name = ma.String(required=True)
    email = ma.Email(required=True)
    telephone = ma.String(required=True)
