from models.user_models import User, Artisan
from core import (
    ma,
    db
)
from .base import BaseSQLAlchemyAutoSchema
from marshmallow import (
    fields,
    pre_load,
    post_dump
)


class ArtisanSchema(BaseSQLAlchemyAutoSchema):
    class Meta:
        model = Artisan
        include_relationships = True
        load_instance = True
        sqla_session = db.session
        include_fk = False

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
            'updated_at',
        )
        load_instance = True
        transient = True
        sqla_session = db.session

        # read only
        dump_only = (
            'created_at',
        )
    artisan_profile = ma.Nested(ArtisanSchema(
        exclude=(
            'booking',
            # 'booking_category',
            # 'user_profile'
        )
    ), dump_only=True)

    @post_dump
    def edit_dump(self, data, *args, **kwargs):
        if not data['artisan_profile']:
            data['artisan_profile'] = None
        return data
