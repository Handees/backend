from flask import request
from uuid import uuid4
from loguru import logger
from marshmallow import INCLUDE

from . import artisan
from core import db
from models.user_models import (
    Artisan,
    Role
)
from models.bookings import BookingCategory
from models.payments import (
    WithdrawalAccounts, Wallet,
    WalletTransaction, WalletTransactionEnum
)
from core.api.bookings import messages
from schemas import (
    ArtisanSchema,
    AddArtisanSchema,
    WithdrawalAccountSchema,
    WalletWithdrawalSchema,
    WalletSchema,
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
from tasks import initiate_withdrawal
from .utils import send_verification_request
from add_extensions import pwd_context


# config logging
setLogger()


@artisan.post('/')
@login_required
@role_required("customer")
def add_new_artisan(current_user):
    with db.session() as sess:
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
            sess.rollback()
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
        new_artisan.wallet = Wallet()

        logger.info("Attempting to create new artisan")
        try:
            sess.add(new_artisan)
            sess.commit()
            resp = ArtisanSchema().dump(new_artisan)
            resp['job_category'] = category.name
        except Exception as e:
            logger.exception(e)
            sess.rollback()
            return error_response(
                500,
                message=messages.INTERNAL_SERVER_ERROR,
                data="An error occurred while trying to create a new artisan"
            )
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

    artisan: Artisan = current_user.artisan_profile
    # send data to premply for verification
    # if artisan.kyc_status == KYCEnum('2'):
    #     return gen_response(
    #         status_code=400,
    #         message=
    #     )
    try:
        resp = send_verification_request(kyc_data, artisan)
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


@artisan.get('/bank_accounts')
@login_required
@role_required("artisan")
def list_artisan_banks(current_user):
    with db.session() as sess:
        artisan: Artisan = current_user.artisan_profile
        accounts = sess.query(WithdrawalAccounts).filter_by(
            artisan_id=artisan.artisan_id
        ).all()
        return gen_response(
            200,
            data=accounts,
            many=True,
            schema=WithdrawalAccountSchema
        )


@artisan.patch('/wallet_pin')
@login_required
@role_required('artisan')
def update_wallet_pin(current_user):
    with db.session() as sess:
        payload = request.get_json(force=True)
        pin = payload.get('pin', None)
        if not pin:
            return error_response(
                400,
                message="Missing required field 'pin'"
                " or no value was set/sent"
            )
        pin_hash = pwd_context.hash(str(pin))
        artisan: Artisan = current_user.artisan_profile
        wallet: Wallet = artisan.wallet
        wallet.pin = pin_hash

        sess.commit()
        return gen_response(
            200,
            data=WalletSchema().dump(wallet)
        )


@artisan.post('/withdraw')
@login_required
@role_required('artisan')
def withdraw(current_user):
    with db.session() as sess:
        payload = request.get_json(force=True)
        schema = WalletWithdrawalSchema()
        try:
            payload = schema.load(payload)
        except Exception as e:
            return error_response(400, message=str(e))

        wallet = current_user.artisan_profile.wallet
        if wallet:
            # verify pin
            if not pwd_context.verify(payload['pin'], wallet.pin):
                return error_response(
                    400, message="Wrong wallet pin specified"
                )
            if wallet.balance < payload['amount']:
                return error_response(
                    400,
                    message="~Insufficient funds~ Dude you're broke! - 💀"
                )
            new_wallet_transaction = WalletTransaction(
                amount=payload['amount'],
                transaction_type=WalletTransactionEnum.WITHDRAWAL
            )
            sess.add(new_wallet_transaction)
            sess.commit()

            # schedule transfer job
            job_payload = {
                'wallet_transaction_id': new_wallet_transaction.id,
                'amount': payload['amount'],
                'account_id': payload['withdrawal_account_id'],
                'artisan_id': current_user.artisan_profile.artisan_id,
                'user_id': current_user.user_id
            }
            initiate_withdrawal(job_payload)
            return gen_response(
                200, message="Withdrawal Initiated successfully"
            )
        else:
            logger.error(
                f"Weird! - User with id {current_user.user_id}"
                " has no wallet"
            )
