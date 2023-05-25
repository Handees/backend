from models.user_models import (
    User, Artisan
)
from models.bookings import categories
from core import (
    ma,
    db
)
from .base import BaseSQLAlchemyAutoSchema
from . import CardAuthSchema
from marshmallow import (
    fields,
    pre_load,
    post_dump
)


class ArtisanSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Artisan
        load_instance = True
        include_fk = True
        include_reltionships = True

        # read only
        dump_only = (
            'user_id',
            'artisan_id'
        )

        # additional fields
        additional_fields = (
            'user_profile_id',
            'job_category'
        )
    created_at = ma.String(dump_only=True, data_key="became_artisan_on")


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

    artisan_profile = ma.Nested(
        ArtisanSchema(exclude=('user_id',))
    )
    cards = ma.Nested(CardAuthSchema, many=True)
    # addresses = ma.Nested()
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
