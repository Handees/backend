import os
import uuid

from models.user_models import User
from models.documents import (
    BlobTypes,
    Blob
)
from .artisan import ArtisanSchema
from .base import (
    BaseSQLAlchemyAutoSchema,
    BaseSchema
)
from core import ma, db
from add_extensions import redis_
from marshmallow import fields
from .payment import FrontEndCardSchema
from utils import generate_presigned_url


class UserSchema(BaseSQLAlchemyAutoSchema):
    def __init__(self, *args, uid=None, session=None, **kwargs):
        self.uid = uid
        self.session = session
        super().__init__(*args, **kwargs)

    class Meta:
        model = User
        include_fk = True
        include_relationships = True
        exclude = (
            'role',
            'role_id',
            'updated_at',
            'bookings', 'payments',
            'ratings_weighted_sum', 'no_of_ratings',
            'reviews'
        )
        load_instance = True

    artisan_profile = fields.Nested(
        ArtisanSchema(exclude=(
            'user_id', 'user_profile',
        ))
    )
    cards = fields.Nested(FrontEndCardSchema, many=True)
    addresses = fields.Nested("AddressSchema", exclude=(
        'user_id', 'user'
    ))
    profile_picture = fields.Method(
        serialize='get_profile_url',
        deserialize='set_profile_url'
    )
    rating = fields.Method(serialize='get_user_rating')
    active_bookings = fields.Method(serialize='get_active_bookings')

    def _get_profile_url(self, blob_id):
        profile_picture_blob = Blob.get_by_id(blob_id, session=db.session())
        return profile_picture_blob.download_url

    def get_profile_url(self, obj):
        image_url = obj.profile_picture
        if not image_url:
            return ''
        blob_id = image_url.split('/')[-1]
        return self._get_profile_url(blob_id)

    def set_profile_url(self, value):
        BUCKET_NAME = os.getenv('BUCKET_NAME')
        FILENAME = value['filename']
        new_blob = Blob(
            filename=FILENAME,
            user_id=self.uid[0],
            blob_type=BlobTypes[value['blob_type']],
            content_type=value['content_type']
        )
        db.session.add(new_blob)
        db.session.flush()
        url = f"https://storage.googleapis.com/{BUCKET_NAME}/{new_blob.blob_id}"
        # save presigned url to schema instance for use in response to api
        self.upload_url = new_blob.upload_url
        return url

    def get_user_rating(self, obj):
        # get system mean
        c = redis_.get('Platform_User_C')
        if c:
            return obj.get_star_rating(c=c)
        return obj.get_star_rating()

    def get_active_bookings(self, obj):
        uid = obj.user_id
        active_bks = User.fetch_active_bookings(uid, session=self.session)
        if not active_bks:
            return []
        for bk in active_bks:
            image_url = bk.get('matched_artisan', {}).get('profile_picture', '')
            if image_url:
                blob_id = image_url.split('/')[-1]
                bk['matched_artisan']['profile_picture'] = self._get_profile_url(blob_id)
        return active_bks

    # load_instance = True
    # transient = True

    # # read only
    # dump_only = (
    #     'created_at',
    # )

    # @post_dump
    # def edit_dump(self, data, *args, **kwargs):
    #     if data:
    #         if 'artisan_profile' in data and data['artisan_profile']:
    #             kyc_status = data['artisan_profile']['kyc_status']
    #             data['artisan_profile']['kyc_status'] = kyc_status
    #     return data


class AddNewUserSchema(BaseSchema):
    user_id = ma.String(required=True)
    first_name = ma.String()
    last_name = ma.String()
    email = ma.Email(required=True)
    telephone = ma.String()
