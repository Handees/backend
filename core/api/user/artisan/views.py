from flask import request
from uuid import uuid4
from loguru import logger

from . import artisan
from core import db
from models.user_models import (
    User,
    Artisan
)
from models.bookings import BookingCategory
from core.api.bookings import messages
from schemas.user_schemas import ArtisanSchema
from core.utils import (
    gen_response,
    error_response,
    setLogger
)
from ..messages import (
    USER_NOT_FOUND,
    ARTISAN_CREATED,
    ARTISAN_NOT_FOUND,
    ARTISAN_PROFILE_UPDATED,
    USER_HAS_ARTISAN_PROFILE
)
from ...auth.auth_helper import (
    login_required,
    role_required
)


# config logging
setLogger()


@artisan.post('/')
@login_required
@role_required("customer")
def add_new_artisan(current_user):
    """create new artisan"""
    data = request.get_json(force=True)

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

    if user.is_artisan:
        logger.debug('yes this i true')
        logger.debug(user.is_artisan)
        db.session.rollback()
        return error_response(
            400,
            message=USER_HAS_ARTISAN_PROFILE
        )

    # ascend user role
    user.upgrade_to_artisan()
    user.is_artisan = 1
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


@artisan.put('/')
@login_required
@role_required("artisan")
def edit_artisan_profile(current_user):
    """edit profile for artisan"""
    data = request.get_json(force=True)

    # fetch artisan profile
    artisan = current_user.artisan_profile

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


@artisan.get('/')
@login_required
@role_required("artisan")
def get_artisan_profile(current_user):
    """ fetch artisan profile """
    artisan = current_user.artisan_profile

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
