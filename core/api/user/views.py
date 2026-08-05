from flask import request
from sqlalchemy import desc, select
from sqlalchemy.exc import IntegrityError
from loguru import logger
import sys

from devices import save_device_data
from . import user
from core import db
from utils import decode_id
from models.user_models import (
    Permission,
    User
)
from models.payments import CardAuth
from models.reviews import Reviews
from utils import (
    gen_response,
    error_response,
    setLogger,
    paginate
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


logger.remove()
setLogger()


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
        save_device_data(new_user)
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
    payload = request.get_json(force=True)
    schema = UserSchema(
        uid=(
            current_user.user_id,
            current_user.id
        )
    )

    with db.session() as sess:
        try:
            user_data = schema.load(
                payload,
                instance=current_user,
                session=sess,
                partial=True
            )
            sess.commit()
        except Exception as e:
            logger.exception(e)
            sess.rollback()
            return error_response(
                400,
                message=str(e)
            )
        else:
            logger.debug('profile_picture' in payload)
            logger.debug(payload)
            resp = schema.dump(current_user)
            print('profile_picture' in payload, payload)
            # if profile picture changed, return upload presigned url
            if 'profile_picture' in payload:
                logger.debug('PROFILE PHOto WAS UPDATED!!!!')
                print("YES PROFILE PHOTO WAS UPDATED")
                resp = {
                    **resp,
                    'upload_url': schema.upload_url
                }
                print(resp)
            return gen_response(
                200,
                data=resp,
                message=USER_PROFILE_UPDATED
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


@user.post('/app_token')
@login_required
def add_app_token(current_user):
    payload = request.get_json(force=True)
    if 'app_token' not in payload:
        return error_response(
            400,
            'Missing required field "app_token"'
        )
    with db.session() as sess:
        current_user.mobile_app_registration_token = payload['app_token']
        sess.commit()
    return gen_response(200, 'Added token successfully!')

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
    with db.session() as sess:
        schema = UserSchema(session=sess)
        return gen_response(
            200,
            data=schema.dump(current_user)
        )


@user.get('/bookings')
@login_required
@permission_required(Permission.service_request)
def fetch_bookings_for_user(current_user):
    """ fetch all bookings made by a user """
    query = current_user.bookings.order_by(
        desc(Booking.created_at)
    )

    pagination = paginate(
        query=query,
        page=request.args.get("page", 1, type=int),
        per_page=request.args.get("per_page", 10, type=int),
    )

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
        data={
                "bookings": schema.dump(pagination.items),
                "page": pagination.page,
                "per_page": pagination.per_page,
                "total": pagination.total,
                "pages": pagination.pages
            },
        message=msg,
 
    )


# @user.patch('/')
# @login_required
# def update_user_profile(current_user):
#     payload = request.get_json(force=True)
#     schema = UserSchema(load_instance=True)
#     try:
#         schema.load(
#             payload,
#             instance=current_user,
#             partial=True
#         )
#         db.session.commit()
#     except Exception as e:
#         logger.error(e)
#         return error_response(
#             500,
#             message="Unexpected Error occurred whilst updating user profile💀"
#         )
#     else:
#         logger.debug('profile_picture' in payload)
#         logger.debug(payload)
#         resp = schema.dump(current_user)
#         print('profile_picture' in payload, payload)
#         # if profile picture changed, return upload presigned url
#         if 'profile_picture' in payload:
#             logger.debug('PROFILE PHOto WAS UPDATED!!!!')
#             print("YES PROFILE PHOTO WAS UPDATED")
#             resp = {
#                 **resp,
#                 'upload_url': schema.upload_url
#             }
#             print(resp)
#         return gen_response(
#             200,
#             data=resp,
#             message=USER_PROFILE_UPDATED
#         )


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


@user.get('/reviews')
@login_required
def fetch_reviews(current_user):
    with db.session() as sess:
        try:
            cursor = request.args.get('after_id', '', type=str)
            per_page = request.args.get('per_page', 10, type=int)
        except ValueError:
            return error_response(400, message='Invalid query param specified')
        if cursor:
            cursor = decode_id(cursor)
            print(cursor)
            reviews = Reviews.get_all_by_user(
                current_user, sess, cursor, per_page
            )
        else:
            reviews = Reviews.get_all_by_user(
                current_user, sess, per_page=per_page
            )
        return gen_response(200, reviews)
