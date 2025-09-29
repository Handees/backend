from flask import request
from sqlalchemy import desc, select
from sqlalchemy.exc import IntegrityError
from loguru import logger
import sys

from . import user
from core import db
from models.user_models import (
    Permission,
    User
)
from models.payments import CardAuth
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
from schemas.payment import FrontEndCardSchema
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
        new_user = User(**user_data)
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
    except IntegrityError as e:
        logger.exception(e)
        db.session.rollback()
        return error_response(
            400,
            message=USER_DATA_EXISTS
        )
    finally:
        db.session.close()


@user.patch('/')
@login_required
def edit_user(current_user):
    data = request.get_json(force=True)
    schema = UserSchema(
        uid=(
            current_user.user_id,
            current_user.id
        )
    )

    with db.session() as sess:
        try:
            user_data = schema.load(
                data,
                instance=current_user,
                session=sess,
                partial=True
            )
            sess.commit()
            return gen_response(
                200,
                data=schema.dump(user_data)
            )
        except Exception as e:
            logger.exception(e)
            sess.rollback()
            return error_response(
                400,
                message=str(e)
            )


@user.get('/cards')
@login_required
def view_cards(current_user):
    cards = CardAuth.query.filter_by(
        user_id=current_user.user_id
    ).all()
    return gen_response(
        200,
        cards,
        schema=FrontEndCardSchema,
        many=True
    )

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
        desc(Booking.created_at)
    ).all()

    msg = 'fetched top recent bookings successfully'
    schema = BookingSchema(
        only=(
            'booking_id',
            'created_at',
            'booking_category',
            'status',
            'artisan',
            'artisan.user_profile.profile_picture',
            'artisan.user_profile.first_name',
            'artisan.user_profile.last_name',
            'artisan.artisan_id'
        ),
        many=True
    )

    return gen_response(
        200,
        data=schema.dump(bookings),
        message=msg
    )


@user.patch('/')
@login_required
def update_user_profile(current_user):
    payload = request.get_json(force=True)
    schema = UserSchema(load_instance=True)
    try:
        schema.load(
            payload,
            instance=current_user,
            partial=True
        )
        db.session.commit()
    except Exception as e:
        logger.error(e)
        return error_response(
            500,
            message="Unexpected Error occurred whilst updating user profile💀"
        )
    else:
        return gen_response(
            200,
            data=schema.dump(current_user),
            message=USER_PROFILE_UPDATED
        )


@user.get('/cards')
@login_required
def fetch_cards(current_user):
    with db.session() as sess:
        q = select(CardAuth).where(
            CardAuth.user_id == current_user.user_id
        )
        cards = sess.scalars(q)
        return gen_response(
            200,
            cards,
            schema=FrontEndCardSchema,
            many=True
        )


@user.get('/cards/<card_sig>')
@login_required
def fetch_card(current_user, card_sig):
    with db.session() as sess:
        q = select(CardAuth).where(
            CardAuth.signature == card_sig
        )
        card = sess.scalar(q)
        if not card:
            logger.error(f"Card with signature {card_sig} not found")
            return error_response(
                404,
                message="Card not found"
            )
        return gen_response(
            200,
            data=FrontEndCardSchema().dump(card)
        )


@user.delete('/cards/<card_sig>')
@login_required
def delete_card(current_user, card_sig):
    with db.session() as sess:
        q = select(CardAuth).where(
            CardAuth.signature == card_sig
        )
        card = sess.scalar(q)
        if not card:
            logger.error(f"Card with signature {card_sig} not found")
            return error_response(
                404,
                message="Card not found"
            )
        sess.delete(card)
        try:
            sess.commit()
        except Exception as e:
            logger.exception(e)
            sess.rollback()
            return error_response(500, message=str(e))
        return gen_response(200, message="Delete card operation successful")
