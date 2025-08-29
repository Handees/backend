import uuid

from marshmallow import fields

from models.documents import Blob, BlobTypes
from .base import BaseSQLAlchemyAutoSchema
from core import ma, db

# from loguru import logger


class UnitUploadImageFileSchema(ma.Schema):
    filename = fields.Str(required=True)
    content_type = fields.Str(required=True)
    blob_type = fields.Enum(BlobTypes, required=True)


class UnitDownloadImageFileSchema(ma.Schema):
    filename = fields.Str(required=True)
    blob_type = fields.Enum(BlobTypes, required=True)


class ImageFileSchema(ma.Schema):
    images = fields.Raw()

    def __init__(self, *args, action='upload', **kwargs):
        super().__init__(*args, **kwargs)
        if action == 'upload':
            self.fields['images'] = fields.List(
                fields.Nested(UnitUploadImageFileSchema)
            )
        elif action == 'download':
            self.fields['images'] = fields.List(
                fields.Nested(UnitDownloadImageFileSchema)
            )


class BlobSchema(BaseSQLAlchemyAutoSchema):
    def __init__(self, *args, action='upload', **kwargs):
        self.action = action
        super().__init__(*args, **kwargs)

    class Meta:
        model = Blob
        include_fk = True
        load_instance = True
        sqla_session = db.session
    blob_id = fields.String(dump_only=True)
    url = fields.Method(serialize="get_url", dump_only=True)

    def get_url(self, obj):
        if self.action == 'upload':
            return obj.upload_url
        return obj.download_url
