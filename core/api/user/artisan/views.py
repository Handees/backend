from flask import request
from uuid import uuid4
from loguru import logger

from . import artisan
from core import db
from models.user_models import (
    Artisan,
    Role
)
from models.bookings import BookingCategory
from core.api.bookings import messages
from schemas import (
    ArtisanSchema,
    AddArtisanSchema,
    KYC
    # KYCToStore
)
from utils import (
    gen_response,
    error_response,
    setLogger
)
from ..messages import (
    ARTISAN_CREATED,
    ARTISAN_NOT_FOUND,
    ARTISAN_PROFILE_UPDATED,
    ARTISAN_KYC_DATA_INVALID,
    ARTISAN_KYC_PROCESSING,
    USER_HAS_ARTISAN_PROFILE
)
from ...auth.auth_helper import (
    login_required,
    role_required
)
from .utils import send_verification_request


# config logging
setLogger()


@artisan.post('/')
@login_required
@role_required("customer")
def add_new_artisan(current_user):
    """create new artisan"""
    data = request.get_json(force=True)
    user = current_user
    schema = AddArtisanSchema()

    try:
        data = schema.load(data)
    except Exception:
        return error_response(
            400,
            message=schema.error_messages
        )

    # add category rel
    category = BookingCategory.get_by_name(data['job_category'])
    if not category:
        return error_response(404, message=messages.dynamic_msg(
            messages.CATEGORY_NOT_FOUND, data['job_category']
        ))

    new_artisan = Artisan(
        job_title=data['job_title'],
        hourly_rate=data['hourly_rate']
    )

    if user.is_artisan or user.role == Role.get_by_name("artisan"):
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
    new_artisan.booking_category = category

    logger.info("Attempting to create new artisan")
    try:
        db.session.add(new_artisan)
        db.session.commit()

        resp = ArtisanSchema().dump(new_artisan)
    except Exception as e:
        db.session.rollback()
        logger.error("Error occurred while attempting to create new artisan")
        logger.error(e)
    finally:
        db.session.close()

    return gen_response(
        201,
        data=resp,
        message=ARTISAN_CREATED
    )


@artisan.patch('/')
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


@artisan.post('/kyc')
@login_required
@role_required("artisan")
def init_kyc_process(current_user):
    schema = KYC()
    data = request.get_json()
    try:
        kyc_data = schema.load(data)
    except Exception as e:
        logger.error(f'{current_user.user_id} - {ARTISAN_KYC_DATA_INVALID}')
        return error_response(
            400,
            message=ARTISAN_KYC_DATA_INVALID,
            data=str(e)
        )
    # send data to premply for verification
    try:
        resp = send_verification_request(kyc_data, current_user.artisan_profile)
        print(resp)
        return gen_response(
            202,
            message=ARTISAN_KYC_PROCESSING
        )
    except Exception as e:
        logger.error(e)
        return error_response(
            500,
            message=messages.INTERNAL_SERVER_ERROR
        )
