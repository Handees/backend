from models.user_models import User, Artisan
from core import db
from .base import BaseSQLAlchemyAutoSchema
from marshmallow import fields, pre_load


class UserSchema(BaseSQLAlchemyAutoSchema):
    class Meta:
        model = User
        exclude = (
            'role',
            'role_id',
            'updated_at'
        )
        include_fk = True
        include_relationships = True
        load_instance = True
        sqla_session = db.session
        load_relationships = True

        # read only
        dump_only = (
            'created_at',
            'user_id'
        )


class ArtisanSchema(BaseSQLAlchemyAutoSchema):
    class Meta:
        model = Artisan
        include_fk = True
        include_relationships = True
        load_instance = True
        sqla_session = db.session
        load_relationships = True

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
