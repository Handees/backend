from flask import request
from sqlalchemy.exc import IntegrityError
from loguru import logger
from uuid import uuid4
import sys

from . import user
from core import db
from models.user_models import (
    Permission,
    Artisan
)
from core.utils import (
    gen_response,
    error_response,
    LOG_FORMAT,
    _level
)
from schemas.user_schemas import UserSchema
from schemas.bookings_schema import BookingSchema
from .messages import (
    USER_CREATED,
    USER_EMAIL_EXISTS,
    USER_PROFILE_UPDATED
)
from models.bookings import Booking
from core.api.auth.auth_helper import (
    login_required,
    permission_required,
    role_required
)


logger.add(
    sys.stderr,
    colorize=True,
    level=_level,
    format=LOG_FORMAT
)


@user.route('/', methods=['POST'])
def create_new_user():
    """ adds new user data to db """
    data = request.get_json(force=True)
    schema = UserSchema()
    try:
        new_user = schema.load(data)
        if new_user.is_artisan:
            new_user.upgrade_to_artisan()
            # create artisan profile
            artisan_profile = Artisan(
                artisan_id=uuid4().hex
            )
            artisan_profile.user_profile = new_user

            db.session.add(artisan_profile)
        # if 'uid' not in data.keys():
        #     new_user.user_id = uuid4().hex
    except Exception as e:
        logger.exception(e)
        return error_response(
            400,
            message=schema.error_messages
        )

    try:
        db.session.add(new_user)
        db.session.commit()
        return gen_response(
            201,
            data=schema.dump(new_user),
            message=USER_CREATED
        )
    except IntegrityError:
        return error_response(
            400,
            message=USER_EMAIL_EXISTS
        )


@user.get('/bookings')
@login_required
@permission_required(Permission.service_request)
def fetch_bookings_for_user(current_user):
    """ fetch all bookings made by a user """
    bookings = current_user.bookings.order_by(
        Booking.date_of_booking
    ).limit(10).all()

    msg = 'fetched top recent bookings successfully'

    return gen_response(
        200,
        data=BookingSchema(many=True).dump(bookings),
        message=msg
    )


@user.patch('/')
@login_required
@role_required("customer")
def update_user_profile(current_user):
    payload = request.get_json(force=True)
    schema = UserSchema()

    try:
        user = schema.load(payload, instance=current_user)
        db.session.commit()
    except Exception as e:
        logger.error(e)

    return gen_response(
        200,
        data=schema.dump(user),
        message=USER_PROFILE_UPDATED
    )


# @user.get('/fetch_uid')
# def get_uid():
#     if 
