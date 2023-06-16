from .base import BaseSQLAlchemyAutoSchema
from core import (
    ma, db
)
from models.bookings import (Booking, BookingContractDurationEnum)
from marshmallow import pre_load
from marshmallow import fields
from geoalchemy2.types import Geometry as GeometryType
from marshmallow_sqlalchemy import ModelConverter
from core.exc import DataValidationError
from schemas.utils import v_float


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
        sqla_session = db.session
        dump_only = (
            'booking_id',
            'created_at', 'settlement_type'
        )
        model_converter = BookingModelConverter
        additional = (
            'lat', 'lon',
            'job_category', 'user_id'
        )
        load_instance = True

    job_category = fields.Str(required=True, load_only=True)
    lat = fields.Float(required=True, load_only=True, validate=v_float)
    lon = fields.Float(required=True, load_only=True, validate=v_float)

    # def load(self, *args, **kwargs):
    #     try:
    #         super().load(*args, **kwargs)
    #     except Exception as e:
    #         err = parse_error(e)
    #         error = DataValidationError(
    #             msg=""
    #         )

    @pre_load
    def edit_payload(self, data, **kwargs):
        if data:
            data['location'] = f"SRID=4326;POINT({data['lat']} {data['lon']})"
        return data


class CancelBookingSchema(ma.Schema):
    booking_id = fields.Str(required=True, load_only=True)
    status_code = fields.Integer(required=True, load_only=True)
    artisan_id = fields.Str(required=True, load_only=True)


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
    settlement = fields.Nested(BookingSettlementSchema)
    duration = fields.Integer()
    duration_unit = fields.Str()

    @pre_load
    def verify_unit(self, data, *args, **kwargs):
        if data:
            try:
                BookingContractDurationEnum[data['duration_unit'].upper()]
            except KeyError:
                raise DataValidationError('invalid duration unit passed')
            else:
                data['duration_unit'] = data['duration_unit'].upper()
        return data
