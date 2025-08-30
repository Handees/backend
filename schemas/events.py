import os

from loguru import logger
from marshmallow import fields, pre_load, post_load

from .base import BaseSchema
import utils


class AvailableArtisanSchema(BaseSchema):
    class Meta:
        unknown = 'include'

    artisan_id = fields.Str(data_key='artisan_id')
    category = fields.Str(data_key='job_category')
    hourly_rate = fields.Float(data_key='hourly_rate')
    name = fields.Str(data_key='user_name')
    phone_number = fields.Str(data_key='user_profile.telephone')
    profile_picture = fields.Str(data_key='user_profile.profile_picture')
    rating = fields.Float()

    @pre_load
    def parse(self, data, *args, **kwargs):
        first_name = data['user_profile'].pop('first_name')
        last_name = data['user_profile'].pop('last_name')
        data['user_name'] = f'{first_name} {last_name}'

        # data.pop('user_profile', None)
        return data

    @post_load
    def add_data(self, data, *args, **kwargs):
        if 'profile_picture' in data:
            fname = data['profile_picture'].split('/')[-1]
            url = utils.generate_presigned_url(
                bucket_name=os.getenv('BUCKET_NAME'),
                object_name=fname,
                action='download'
            )
            data['profile_picture'] = url
        return data


class CoordsSchema(BaseSchema):
    lat = fields.Float(required=True)
    lon = fields.Float(required=True)


class AvailableArtisanLocationSchema(BaseSchema):
    time_remaining = fields.Float()
    coordinates = fields.Nested(CoordsSchema)


class BookingAcceptedSchema(BaseSchema):
    booking_id = fields.Str()
    artisan_info = fields.Nested(AvailableArtisanSchema)
    transit_details = fields.Nested(AvailableArtisanLocationSchema)


class BookingUserDetailSchema(BaseSchema):
    class Meta:
        unknown = 'include'

    image = fields.Str(load_default='', data_key='profile_picture')
    name = fields.Str(data_key='user_name')
    phoneNumber = fields.Str(data_key='telephone')
    rating = fields.Float(load_default=0.0)
    address = fields.Str()

    @pre_load
    def parse(self, data, **kwargs):
        first_name = data.pop('first_name')
        last_name = data.pop('last_name')
        data['user_name'] = f'{first_name} {last_name}'
        return data

    @post_load
    def p_parse(self, data, **kwargs):
        to_remove = []
        for k in data.keys():
            if k not in self.fields.keys():
                to_remove.append(k)
        logger.error(to_remove)
        for k in to_remove: data.pop(k, None)
        return data


class NewBookingRequestSchema(BaseSchema):
    class Meta:
        unknown = 'include'

    bookingId = fields.Str(data_key='booking_id')
    category = fields.Str(data_key='job_category')
    lat = fields.Float()
    lon = fields.Float()
    paymentMethod = fields.Str(data_key='payment_method')
    serviceDuration = fields.Float()
    userDetails = fields.Nested(BookingUserDetailSchema)
    coordinates = fields.Nested(CoordsSchema)

    @post_load
    def cleanup(self, data, **kwargs):
        data.pop('location')
        return data

# interface CoordsI {
#   lon: number;
#   lat: number;
# }
# interface OfferAcceptedI {
#   artisanInfo: AvailableArtisanI;
#   location: {
#     arrivalTime: string;
#     coordinates: CoordsI;
#   };
# }
