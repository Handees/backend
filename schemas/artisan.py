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
            'ratings_weighted_sum', 'bookings', 'current_booking_id'
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
        with db.session() as sess:

            rating_counts = sess.query(
                Reviews.weight,
                func.count(Reviews.id)
            ).filter(
                Reviews.artisan_id == obj.artisan_id,
                Reviews.weight.between(1, 5)
            ).group_by(
                Reviews.weight
            ).all()

            # Default 1-5 to 0
            review_grouped = {
                'r1': 0,
                'r2': 0,
                'r3': 0,
                'r4': 0,
                'r5': 0
            }

            # Put actual review counts into r1-r5
            for rating, rating_count in rating_counts:
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

    def _get_profile_url(self, blob_id):
        profile_picture_blob = Blob.get_by_id(blob_id, session=db.session())
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
            print(user_profile, customer_photo, artisan_obj)
        return artisan_obj

    @post_dump
    def add_customer_photo_on_active_bk(self, obj, *args, **kwargs):
        print(obj)
        if obj['current_booking']:
            cb = obj['current_booking']
            cb['customer'] = cb['user']
            del cb['user']
            # cb['customer_profile_picture'] = \
            #     obj['customer_profile_picture']
            print(obj)
            del obj['booking_category']
            cb['booking_category'] = \
                cb['booking_category']['name']
            cb['customer']['address'] = cb['customer_address']
            cb['customer']['profile_picture'] = obj['customer_profile_picture']
            cb['customer']['id'] = cb['customer_id']
            del obj['customer_profile_picture']
            del cb['customer_address']
            del cb['customer_id']
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
