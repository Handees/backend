import uuid

from marshmallow import fields, post_load

from models.documents import Blob, BlobTypes
from .base import BaseSQLAlchemyAutoSchema
from core import ma, db

# from loguru import logger


class ImageFileSchema(ma.Schema):
    filename = fields.Str(required=True)
    content_type = fields.Str(required=True)
    blob_type = fields.Enum(BlobTypes, required=True)


class BlobSchema(BaseSQLAlchemyAutoSchema):
    class Meta:
        model = Blob
        include_fk = True
        load_instance = True
        sqla_session = db.session
    blob_id = fields.String(dump_only=True)
    url = fields.Method(serialize="get_url", dump_only=True)

    def get_url(self, obj):
        return obj.upload_url

