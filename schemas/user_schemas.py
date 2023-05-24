from models.user_models import User, Artisan
from core import (
    ma,
    db
)
from .base import BaseSQLAlchemyAutoSchema
from marshmallow import fields, pre_load


class ArtisanSchema(BaseSQLAlchemyAutoSchema):
    class Meta:
        model = Artisan
        include_fk = True
        include_relationships = True
        load_instance = True
        sqla_session = db.session

        # read only
        dump_only = (
            'created_at',
            'user_id',
            'artisan_id'
        )

        # additional fields
        additional_fields = (
            'user_profile_id',
            'job_category'
        )

    user_profile_id = fields.Field(required=False)

    @pre_load
    def preformat_data(self, data, *args, **kwargs):
        if data:
            del data['job_category']
        return data


class UserSchema(BaseSQLAlchemyAutoSchema):
    class Meta:
        model = User
        exclude = (
            'role',
            'role_id',
            'updated_at'
        )
        load_instance = True
        transient = True
        sqla_session = db.session

        # read only
        dump_only = (
            'created_at'
        )
    artisan_profile = ma.Nested(Artisan(
        only=(
            'artisan_id', 'is_verified',
            'jobs_title', 'jobs_completed',
            'sign_up_date', 'hourly_rate',
            'ratings', 'user_id',
            'job_category_id',
        )
    ), dump_only=True)
