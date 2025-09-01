from marshmallow import fields, pre_load

from core import ma, db
from models.documents import Blob, BlobTypes
from .base import BaseSQLAlchemyAutoSchema
from utils import generate_unique_file_id

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
    def __init__(self, *args, action='upload', uid=None, **kwargs):
        self.action = action
        self.uid = uid
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

    @pre_load
    def add_img_id(self, obj, *args, **kwargs):
        if self.uid:
            obj['img_id'] = generate_unique_file_id(
                user_id=self.uid,
                filename=obj['filename'],
                blob_type=int(BlobTypes[obj['blob_type'].name].value)
            )
        return obj
