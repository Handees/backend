from flask import request
from uuid import uuid4

from . import artisan
from core import db
from models.user_models import (
    User,
    Artisan
)
from models.bookings import BookingCategory
from core.bookings import messages
from schemas.user_schemas import ArtisanSchema
from core.utils import (
    gen_response,
    error_response
)
from ..messages import (
    USER_NOT_FOUND,
    ARTISAN_CREATED,
    ARTISAN_NOT_FOUND,
    ARTISAN_PROFILE_UPDATED,
    USER_HAS_ARTISAN_PROFILE
)


@artisan.post('/')
# will require auth decorators @TODO
# TODO: pass current user to handler
def add_new_artisan():
    """create new artisan"""
    data = request.get_json(force=True)

    db.session.begin()

    # add category rel
    category = BookingCategory.get_by_name(data['job_category'])
    if not category:
        db.session.rollback()
        return error_response(404, message=messages.dynamic_msg(
            messages.CATEGORY_NOT_FOUND, data['job_category']
        ))

    schema = ArtisanSchema()
    try:
        new_artisan = schema.load(data)
    except Exception:
        db.session.rollback()
        raise(Exception)
        return error_response(
            400,
            message=schema.error_messages
        )

    # @dev_only: find user with user_id
    user = User.query.get(data['user_profile_id'])
    if not user:
        db.session.rollback()
        return error_response(
            404,
            message=USER_NOT_FOUND
        )

    if user.is_artisan():
        db.session.rollback()
        return error_response(
            400,
            message=USER_HAS_ARTISAN_PROFILE
        )

    # ascend user role
    user.upgrade_to_artisan()
    new_artisan.user_profile = user

    # add other props
    new_artisan.artisan_id = uuid4().hex
    new_artisan.job_category = category

    db.session.add(new_artisan)
    db.session.commit()

    return gen_response(
        201,
        data=schema.dump(new_artisan),
        message=ARTISAN_CREATED
    )


@artisan.put('/<artisan_id>')
# will require auth decorators @TODO
# TODO: pass current user to handler
def edit_artisan_profile(artisan_id):
    """edit profile for artisan"""
    data = request.get_json(force=True)

    # fetch artisan profile
    artisan = Artisan.query.get(artisan_id)
    if not artisan:
        return error_response(
            404,
            message=ARTISAN_NOT_FOUND
        )

    schema = ArtisanSchema()
    try:
        schema.load(data, instance=artisan)
    except Exception:
        return error_response(
            400,
            message=schema.error_messages
        )

    db.session.commit()

    return gen_response(
        201,
        data=schema.dump(artisan),
        message=ARTISAN_PROFILE_UPDATED
    )


@artisan.get('/<artisan_id>')
# will require auth decorators @TODO
# TODO: pass current user to handler
def get_artisan_profile(artisan_id):
    """ fetch artisan profile """
    artisan = Artisan.query.get(artisan_id)

    if not artisan:
        return error_response(
            404,
            message=ARTISAN_NOT_FOUND
        )

    schema = ArtisanSchema()

    return gen_response(
        200,
        data=schema.dump(artisan)
    )
