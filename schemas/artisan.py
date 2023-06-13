from models.user_models import Artisan
from core import ma
from models.bookings import categories
from .base import (
    BaseSQLAlchemyAutoSchema,
    BaseSchema
)
from marshmallow import (
    fields,
    pre_load,
    post_dump
)


class ArtisanSchema(BaseSQLAlchemyAutoSchema):
    class Meta:
        model = Artisan
        load_instance = True
        include_fk = True
        include_relationships = True

        # read only
        dump_only = (
            'user_id',
            'artisan_id'
        )

        exclude = (
            'booking',
        )

        # additional fields
        additional_fields = (
            'user_profile_id',
            'job_category'
        )
    created_at = ma.String(dump_only=True, data_key="became_artisan_on")
    user_profile = fields.Nested("UserSchema", exclude=(
        'artisan_profile', 'role_id',
        'bookings', 'payments'
    ))

    @pre_load
    def preformat_data(self, data, *args, **kwargs):
        if data:
            del data['job_category']
        return data

    @post_dump
    def append_job_category(self, data, *args, **kwargs):
        if data:
            data['job_category'] = categories[data['job_category_id']]
            del data['job_category_id']
        return data


class AddArtisanSchema(BaseSchema):
    hourly_rate = ma.Float(required=True)
    job_category = ma.String(required=True)
    job_title = ma.String(required=True)
