import contextvars

from models import Reviews
from models.user_models import (
    Artisan,
    Kyc
)
from core import ma, db
from add_extensions import redis_
from models.documents import Blob
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
from sqlalchemy import func


# Define the variable globally. The default is None.
db_session_ctx = contextvars.ContextVar('db_session', default=None)


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
            'ratings_weighted_sum', 'bookings', 'current_booking_id',
            'rating_counts'
        )
    # sign_up_date = ma.String()
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
    current_booking = fields.Nested(
        'BookingSchema',
        only=(
            'booking_id', 'job_category', 'user.first_name',
            'user.last_name', 'description',
            'clock_in_flag', 'lat', 'lon', 'customer_address',
            'settlement_type', 'payment_method', 'contract_type',
            'booking_contract.duration', 'booking_contract.duration_unit',
            'booking_category.name', 'customer_id'
        )
    )
    customer_profile_picture = fields.Str(dump_only=True)


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
        # Default 1-5 to 0
        review_grouped = {
            'r1': 0,
            'r2': 0,
            'r3': 0,
            'r4': 0,
            'r5': 0
        }

        # Put actual review counts into r1-r5
        for rating, rating_count in obj.rating_counts.items():
            review_grouped[f'r{rating}'] = rating_count

        # Total number of reviews
        count = sum(review_grouped.values())

        # Convert counts to percentages
        if count > 0:
            review_grouped = {
                rating: round((rating_count / count) * 100)
                for rating, rating_count in review_grouped.items()
            }

        return {
            'rating': self.get_artisan_rating(obj),
            'activity': obj.activity,
            'earnings': obj.total_earnings,
            'review_matrics': {
                'count': count,
                'review_grouped': review_grouped
            }
        }

    def _get_profile_url(self, blob_id, session=None):
        sess = session or db_session_ctx.get() or db.session()
        profile_picture_blob = Blob.get_by_id(blob_id, session=sess)
        return profile_picture_blob.download_url

    def get_profile_url(self, user_obj):
        image_url = user_obj.profile_picture
        if not image_url:
            return ''
        blob_id = image_url.split('/')[-1]
        return self._get_profile_url(blob_id)

    @pre_dump
    def add_active_bk_details(self, artisan_obj, *args, **kwargs):
        current_booking = artisan_obj.current_booking
        if current_booking:
            user_profile = current_booking.user
            customer_photo = self.get_profile_url(user_profile)
            setattr(artisan_obj, 'customer_profile_picture', customer_photo)
        return artisan_obj

    @post_dump
    def add_customer_photo_on_active_bk(self, obj, *args, **kwargs):
        # 1. Safely grab current_booking; exit early if it's missing or empty
        cb = obj.get('current_booking')
        if not cb:
            return obj

        # 2. Rename 'user' to 'customer', defaulting to an empty dict if missing
        customer_data = cb.pop('user', {})

        # 3. Safely pop variables. If they exist, add them to the customer dictionary
        address = cb.pop('customer_address', None)
        if address is not None:
            customer_data['address'] = address

        cust_id = cb.pop('customer_id', None)
        if cust_id is not None:
            customer_data['id'] = cust_id

        profile_pic = obj.pop('customer_profile_picture', None)
        if profile_pic is not None:
            customer_data['profile_picture'] = profile_pic

        # Assign the compiled customer data back to the booking
        if customer_data:
            cb['customer'] = customer_data

        # 4. Safely remove booking_category from the root obj if it exists
        obj.pop('booking_category', None)

        # 5. Safely flatten the nested booking_category inside current_booking
        bk_cat = cb.get('booking_category')
        if isinstance(bk_cat, dict) and 'name' in bk_cat:
            cb['booking_category'] = bk_cat['name']

        return obj


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
