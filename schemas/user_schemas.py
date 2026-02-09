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
    def __init__(self, *args, uid=None, **kwargs):
        self.uid = uid
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

    def get_profile_url(self, obj):
        url = obj.profile_picture
        if url:
            img_id = obj.profile_picture.split('/')[-1]
            return generate_presigned_url(
                bucket_name=os.getenv('BUCKET_NAME'),
                object_name=img_id,
                action='download'
            )
        return url

    def set_profile_url(self, value):
        BUCKET_NAME = os.getenv('BUCKET_NAME')
        FILENAME = value['filename']
        new_blob = Blob(
            filename=FILENAME,
            user_id=self.uid[0],
            blob_type=BlobTypes[value['blob_type']],
            content_type=value['content_type']
        )
        new_blob.blob_id = uuid.uuid4().hex
        new_blob.set_url_id(self.uid[1])
        img_id = new_blob.img_id
        db.session.add(new_blob)
        db.session.flush()
        url = f"https://storage.googleapis.com/{BUCKET_NAME}/{img_id}"
        return url

    def get_user_rating(self, obj):
        # get system mean
        c = redis_.get('Platform_User_C')
        if c:
            return obj.get_star_rating(c=c)
        return obj.get_star_rating()

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
