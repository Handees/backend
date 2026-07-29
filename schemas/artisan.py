from models.user_models import (
    Artisan,
    Kyc
)
from core import ma
from add_extensions import redis_
from models.bookings import BookingCategory
from .base import (
    BaseSQLAlchemyAutoSchema,
    BaseSchema
)
from marshmallow import (
    fields,
    pre_load,
    post_load,
    pre_dump,
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
            'booking', 'ratings_weighted_sum',
        )

    # additional fields
    created_at = ma.String(dump_only=True, data_key="became_artisan_on")
    user_profile = fields.Nested("UserSchema", only=(
        'telephone', 'rating', 'reviews',
        'first_name', 'last_name', 'profile_picture'
    ))
    job_category = fields.Method(serialize='show_category')
    bank_accounts = fields.Nested(
        'WithdrawalAccountSchema',
        only=(
            'id', 'account_name', 'account_number',
            'bank_name', 'bank_code'
        ),
        many=True
    )
    reviews = fields.Nested('ReviewSchema', only=('weight', 'comment',))
    metrics = fields.Method(serialize='get_metrics')
    rating = fields.Method(serialize='get_artisan_rating', dump_only=True)

    @pre_load
    def preformat_data(self, data, *args, **kwargs):
        if data:
            del data['job_category']
        return data

    def show_category(self, obj):
        return obj.booking_category.name

    def get_artisan_rating(self, obj):
        # get system mean
        c = redis_.get('Platform_Artisan_C')
        if c:
            return obj.get_star_rating(c=c)
        return obj.get_star_rating()

    def get_metrics(self, obj):
        return {
            'rating': self.get_artisan_rating(obj),
            'activity': obj.activity,
            'earnings': obj.total_earnings
        }


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
