from flask import request
from sqlalchemy.exc import IntegrityError
from uuid import uuid4
from loguru import logger
import sys

from . import user
from core import db
from models.user_models import (
    User,
    Permission
)
from ..utils import (
    gen_response,
    error_response
)
from schemas.user_schemas import UserSchema
from .messages import (
    USER_CREATED,
    USER_EMAIL_EXISTS
)
from models.bookings import Booking
from core.utils import (
    LOG_FORMAT,
    _level
)
# from auth.auth_helper import login_required, permission_required


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
        # if 'uid' not in data.keys():
        #     new_user.user_id = uuid4().hex
    except Exception as e:
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
# @login_required
# @permission_required(Permission.service_request)
def fetch_bookings_for_user(current_user):
    """ fetch all bookings made by a user """
    bookings = Booking.query.filter_by(current_user.user_id).order_by(
        Booking.date_of_booking
    ).limit(10).all()

    msg = 'fetched top recent bookings successfully'

    return gen_response(
        200, bookings,
        message=msg,
        many=True,
        use_schema=True
    )


@user.patch('/')
# @login_required
# @permission_required(Permission.service_request)
def update_user_profile(current_user):
    data = request.get_json(force=True)
    return current_user.update_profile(params=data)
