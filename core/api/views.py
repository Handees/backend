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
        for img in images:
            img.blob_id = uuid.uuid4().hex
        sess.add_all(images)
        sess.commit()

        resp = BlobSchema(
            only=('filename', 'url'),
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
            imgs = ImageFileSchema(
                action='download'
            ).load(data)
        except Exception as e:
            return error_response(
                status_code=400,
                message=str(e)
            )
        to_be_downloaded = []
        for img in imgs['images']:
            query = select(Blob).where(
                and_(
                    Blob.blob_type == img['blob_type'],
                    Blob.user_id == current_user.user_id,
                    Blob.filename == img['filename']
                )
            )
            blob = sess.scalars(query).first()
            if not blob:
                return error_response(
                    404,
                    f"""
                        Blob with filename {img['filename']} 
                        and matching blob type {img['blob_type']}
                        not found. It likely hasn't been uploaded.
                    """
                )
            to_be_downloaded.append(blob)

        resp = BlobSchema(
            only=('filename', 'url'),
            action='download',
            many=True
        ).dump(to_be_downloaded)
        return gen_response(
            200,
            data=resp
        )
