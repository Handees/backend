import uuid

from flask import request

from . import api
from core import db
from utils import (
    gen_response,
    error_response,
)
from core.api.auth.auth_helper import login_required
from schemas.generic import ImageFileSchema, BlobSchema


@api.post('/upload_url')
@login_required
def request_presigned_urls(current_user):
    _base_img = {
        'user_id': current_user.user_id
    }
    with db.session() as sess:
        data = request.get_json(force=True)
        try:
            img = ImageFileSchema().load(data)
        except Exception as e:
            return error_response(
                status_code=400,
                message=str(e)
            )
        to_be_uploaded = {**_base_img, **img}
        images_schema = BlobSchema()
        image = images_schema.load(to_be_uploaded)
        image.blob_id = uuid.uuid4().hex
        sess.add(image)
        sess.commit()

        resp = BlobSchema(
            only=('filename', 'url')
        ).dump(image)
        return gen_response(
            200,
            data=resp
        )
