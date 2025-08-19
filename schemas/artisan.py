from models.user_models import (
    Artisan,
    Kyc
)
from core import ma
from models.bookings import BookingCategory
from .base import (
    BaseSQLAlchemyAutoSchema,
    BaseSchema
)
from marshmallow import (
    fields,
    pre_load,
    post_load,
    validate,
    post_dump,
    INCLUDE
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

        # additional field
    created_at = ma.String(dump_only=True, data_key="became_artisan_on")
    user_profile = fields.Nested("UserSchema", exclude=(
        'artisan_profile', 'role_id',
        'bookings', 'payments', 'cards',
        'addresses'
    ))

    @pre_load
    def preformat_data(self, data, *args, **kwargs):
        if data:
            del data['job_category']
        return data

    @post_dump
    def edit_dump(self, data, *args, **kwargs):
        # TODO: remove this and fix parsing from on-set
        if 'job_category_id' in data:
            cat = BookingCategory.query.get(data['job_category_id'])
            data['job_category'] = cat.name
        return data


class AddArtisanSchema(BaseSchema):
    hourly_rate = ma.Float(required=True)
    job_category = ma.String(required=True)
    job_title = ma.String(required=True)


class KYCToStore(BaseSQLAlchemyAutoSchema):
    class Meta:
        model = Kyc
        # load_instance = True
        # include_fk = True
        # include_relationships = True


class KYCWithFace(BaseSchema):
    image = ma.String(
        required=True,
        validate=validate.URL(
            schemes=['https'],
            error="Invalid Image URL, please check to ensure its a secure url format e.g"
            " (https://<hostname>/<path_to_image_resource>)"
        )
    )


class Nin(KYCWithFace):
    number = ma.String(required=True, validate=validate.Length(equal=11))


class DriversLicense(KYCWithFace):
    number = ma.String(required=True, validate=validate.Length(equal=11))
    date_of_birth = ma.DateTime(required=True)


class Passport(KYCWithFace):
    number = ma.String(required=True, validate=validate.Length(equal=10))
    last_name = ma.String(required=True)


class KYC(BaseSchema):
    kyc_type = ma.String(required=True, validate=validate.OneOf(
        choices=["nin", "drivers_license", "passport"]
    ))

    class Meta:
        unknown = INCLUDE

    _options = {
        'nin': Nin,
        'drivers_license': DriversLicense,
        'passport': Passport
    }

    @pre_load
    def preformat_data(self, data, *args, **kwargs):
        if data and 'kyc_type' in data:
            data['kyc_type'] = data['kyc_type'].lower()
        return data

    @post_load
    def format_data(self, data, *args, **kwargs):
        option = data['kyc_type']
        del data['kyc_type']
        new_data = KYC._options[option]().load(data)
        new_data['kyc_type'] = option
        return new_data
