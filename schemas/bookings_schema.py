from sqlalchemy import func
from marshmallow import fields
from geoalchemy2.types import Geometry as GeometryType
from geoalchemy2.elements import WKTElement
from marshmallow_sqlalchemy import ModelConverter

from .base import BaseSQLAlchemyAutoSchema
from core import (
    ma,
    db
)
from models.bookings import (
    Booking,
    BookingContractDurationEnum,
    BookingPaymentMethod,
    BookingWorkSession,
    BookingContract,
    BookingCategory,
    BookingWorkDay
)
from marshmallow import (
    pre_load,
    post_load,
    pre_dump
)
from core.exc import DataValidationError
from schemas.schema_utils import v_float
from schemas.generic import BlobSchema


class BookingContractSchema(BaseSQLAlchemyAutoSchema):
    class Meta:
        model = BookingContract


class BookingCategorySchema(BaseSQLAlchemyAutoSchema):
    class Meta:
        model = BookingCategory


class UploadImagesSchema(ma.Schema):
    files = fields.Nested('UnitUploadImageFileSchema', many=True)
    #TODO: verify blob type


class BookingModelConverter(ModelConverter):
    """Helps to serialize geometry column types"""
    # https://stackoverflow.com/questions/34894170/difficulty-serializing-geography-column-type-using-sqlalchemy-marshmallow
    SQLA_TYPE_MAPPING = {
        **ModelConverter.SQLA_TYPE_MAPPING,
        **{GeometryType: fields.Str},
    }


class BookingSchema(BaseSQLAlchemyAutoSchema):
    class Meta:
        # TODO: remove 'user-id' from additional fields
        # once auth has been implemented
        model = Booking
        include_fk = True
        include_relationships = True
        transient = True
        dump_only = (
            'booking_id',
            'created_at', 'settlement_type',
            'status', 'contract_type',
            'artisan_rating', 'customer_rating'
        )
        model_converter = BookingModelConverter
        additional = (
            'lat', 'lon',
            'job_category', 'user_id'
        )
        load_instance = True

    job_category = fields.Str(required=True, load_only=True)
    lat = fields.Float(required=True, validate=v_float)
    lon = fields.Float(required=True, validate=v_float)
    payment_method = fields.Enum(BookingPaymentMethod)
    images = fields.Method(serialize='show_upload_url')
    artisan = fields.Nested('ArtisanSchema')
    user = fields.Nested('UserSchema', only=('first_name', 'last_name'))
    booking_contract = fields.Nested(BookingContractSchema)
    booking_category = fields.Nested(BookingCategorySchema)

    def show_upload_url(self, obj):
        return BlobSchema(
            many=True,
            only=('url', 'filename', 'content_type')
        ).dump(obj.images)

    @pre_load
    def format(self, data, *args, **kwargs):
        if data:
            if 'payment_method' not in data:
                raise DataValidationError(
                    'Required Field payment_method missing'
                )
            curr_method = data['payment_method']
            if curr_method.lower().strip() == 'card':
                data['payment_method'] = 'CARD'
            else:
                data['payment_method'] = 'CASH'
        return data

    # def load(self, data, *args, **kwargs):
    #     try:
    #         super().load(data, *args, **kwargs)
    #     except Exception as e:
    #         logger.exception(e)
    #         raise e
    #         # err = parse_error(e)
    #         # error = DataValidationError(
    #         #     msg=""
    #         # )

    @pre_load
    def edit_payload(self, data, **kwargs):
        if data:
            if 'lat' not in data:
                raise DataValidationError(
                    "Required Field 'lat' missing"
                )
            if 'lon' not in data:
                raise DataValidationError(
                    "Required Field 'lon' missing"
                )
            data['location'] = f"SRID=4326;POINT({data['lat']} {data['lon']})"
        return data


class CancelBookingSchema(ma.Schema):
    booking_id = fields.Str(required=True, load_only=True)


class BookingSettlementSchema(ma.Schema):
    type: str = fields.Str(required=True)
    amount: float = fields.Float()

    @pre_load
    def transform_type(self, data, *args, **kwargs):
        if data:
            data['type'] = data['type'].upper()
        return data


class BookingStartSchema(ma.Schema):
    booking_id = fields.Str(required=True)
    is_contract = fields.Boolean(required=True)
    settlement = fields.Nested(BookingSettlementSchema, required=True)
    duration = fields.Integer()
    duration_unit = fields.Str()

    @post_load
    def verify_unit(self, data, *args, **kwargs):
        if data:
            if data['is_contract']:
                if 'duration' not in data or 'duration_unit' not in data:
                    raise DataValidationError('Missing fields: <duration_unit> or <duration> or both')
                # validate units for duration if contract type
                try:
                    if data['duration_unit'].lower().strip() not in ['days', 'weeks']:
                        raise DataValidationError('invalid duration unit passed, check spelling')
                    BookingContractDurationEnum[data['duration_unit'].upper()]
                    data['duration_unit'] = data['duration_unit'].upper()
                except ValueError:
                    raise DataValidationError('invalid duration unit passed - ensure type is <str>')
                except KeyError:
                    raise DataValidationError('Missing field: <duration_unit>')

            if data['settlement']['type'].lower().strip() not in ['hourly_rate', 'negotiation']:
                raise DataValidationError("Invalid settlement type specified: check spelling")
            if data['settlement']['type'].lower().strip() == 'negotiation':
                if 'amount' not in data['settlement']:
                    raise DataValidationError("Missing Field: <amount>, please specify the negotiated amount")
                elif 'amount' in data['settlement'] and not (data['settlement']['amount'] > 500):
                    raise DataValidationError("Invalid settlement amount passed")
        return data


class BookingWorkDaySchema(BaseSQLAlchemyAutoSchema):
    class Meta:
        model = BookingWorkDay
        include_fk = True
        include_relationships = True
        load_instance = True
        sqla_session = db.session

    work_sessions = fields.Nested(
        'BookingWorkSessionSchema',
        only=('clock_in', 'clock_out',),
        many=True
    )


class BookingWorkSessionSchema(BaseSQLAlchemyAutoSchema):
    class Meta:
        model = BookingWorkSession
        include_fk = True
