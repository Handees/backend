import uuid

from flask import request
from sqlalchemy import select, and_

from . import api
from core import db
from models import Blob
from utils import (
    gen_response,
    error_response,
)
from schemas.generic import (
    ImageFileSchema, BlobSchema
)
from core.api.auth.auth_helper import login_required


@api.post('/upload_url')
@login_required
def request_upload_urls(current_user):
    _base_img = {
        'user_id': current_user.user_id
    }
    with db.session() as sess:
        data = request.get_json(force=True)
        try:
            data = ImageFileSchema().load(data)
        except Exception as e:
            return error_response(
                status_code=400,
                message=str(e)
            )
        to_be_uploaded = data['images']
        for idx, obj in enumerate(to_be_uploaded):
            to_be_uploaded[idx] = {
                **_base_img,
                **obj
            }
        images_schema = BlobSchema(many=True)
        images = images_schema.load(to_be_uploaded)
        sess.add_all(images)
        sess.commit()

        resp = BlobSchema(
            only=('filename', 'blob_id', 'url'),
            many=True
        ).dump(images)
        return gen_response(
            200,
            data=resp
        )


@api.post('/download_url')
@login_required
def request_download_urls(current_user):
    with db.session() as sess:
        data = request.get_json(force=True)
        try:
            imgs = ImageFileSchema(action='download').load(data)
        except Exception as e:
            return error_response(status_code=400, message=str(e))

        to_be_downloaded = []
        for img in imgs['images']:
            # Fetch the exact blob using the primary key
            blob = sess.get(Blob, img['blob_id'])

            # Security check: ensure the current user actually owns this blob
            if not blob or blob.user_id != current_user.user_id:
                return error_response(
                    404,
                    f"File not found or access denied."
                )
            to_be_downloaded.append(blob)

        resp = BlobSchema(
            only=('blob_id', 'filename', 'url'),
            action='download',
            many=True
        ).dump(to_be_downloaded)
        
        return gen_response(200, data=resp)
