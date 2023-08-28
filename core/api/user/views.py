from flask import request
from sqlalchemy.exc import IntegrityError
from loguru import logger
import sys

from . import user
from core import db
from models.user_models import (
    Permission,
    User
)
from utils import (
    gen_response,
    error_response,
    LOG_FORMAT,
    _level
)
from schemas.user_schemas import (
    AddNewUserSchema,
    UserSchema
)
from schemas.bookings_schema import BookingSchema
from .messages import (
    USER_CREATED,
    USER_DATA_EXISTS,
    USER_PROFILE_UPDATED
)
from models.bookings import Booking
from core.api.auth.auth_helper import (
    login_required,
    permission_required
)


logger.add(
    sys.stderr,
    colorize=True,
    level=_level,
    format=LOG_FORMAT
)


@user.post('/')
def create_new_user():
    """ adds new user data to db """
    data = request.get_json(force=True)
    schema = AddNewUserSchema()
    try:
        user_data = schema.load(data)
        new_user = User(
            user_id=user_data['user_id'],
            name=user_data['name'],
            email=user_data['email'],
            telephone=user_data['telephone']
        )
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
        db.session.rollback()
        return error_response(
            400,
            message=USER_DATA_EXISTS
        )
    finally:
        db.session.close()


# @user.get('/<uid>')
# def check_uid(uid):
#     """ checks if uid exists """
#     user = User.query.get(uid)
#     schema = UserSchema()
#     if user:
#         return gen_response(
#             200,
#             data=schema.dump(user)
#         )
#     else:
#         return error_response(
#             404,
#             message=USER_NOT_FOUND
#         )


@user.get('/signin')
@login_required
def fetch_user(current_user):
    """ checks if uid exists """
    schema = UserSchema()
    return gen_response(
        200,
        data=schema.dump(current_user)
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
