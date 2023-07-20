from .base import BaseSQLAlchemyAutoSchema
from core import (
    ma, db
)
from models.bookings import (Booking, BookingContractDurationEnum)
from marshmallow import pre_load, post_load
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
                    if data['duration_unit'].lower() not in ['days', 'weeks']:
                        raise DataValidationError('invalid duration unit passed, check spelling')
                    BookingContractDurationEnum[data['duration_unit'].upper()]
                    data['duration_unit'] = data['duration_unit'].upper()
                except ValueError:
                    raise DataValidationError('invalid duration unit passed - ensure type is <str>')
                except KeyError:
                    raise DataValidationError('Missing field: <duration_unit>')

            if data['settlement']['type'].lower() not in ['hourly_rate', 'negotiation']:
                raise DataValidationError("Invalid settlement type specified: check spelling")
            if data['settlement']['type'].lower() == 'negotiation':
                if 'amount' not in data['settlement']:
                    raise DataValidationError("Missing Field: <amount>, please specify the negotiated amount")
                elif 'amount' in data['settlement'] and not (data['settlement']['amount'] > 500):
                    raise DataValidationError("Invalid settlement amount passed")
        return data
