from models.user_models import (
    Permission,
    Role,
    User
)

from functools import wraps
from flask import (
    abort,
    request,
    make_response
)
from firebase_admin import auth
from firebase_admin.auth import (
    InvalidIdTokenError,
    ExpiredIdTokenError,
    RevokedIdTokenError,
    CertificateFetchError
)
from loguru import logger
from core.utils import setLogger
import os
import json

setLogger()


def permission_required(permission):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            print(args[0].can(permission))
            print(args[0])
            if not args[0].can(permission):
                logger.debug('User permission not allowed')
                resp = make_response({
                    'status': 'error',
                    'msg': 'User cannot perform this action'
                }, 403)
                abort(resp)
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def role_required(role):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            print(args[0].role, args[0])
            if not args[0].role == Role.get_by_name(role):
                logger.debug('User role not allowed')
                resp = make_response(
                    {
                        'status': 'error',
                        'msg': 'user-role cannot perform this action'
                    },
                    403
                )
                abort(resp)
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def admin_required(f):
    return permission_required(Permission.ADMIN)(f)


def paystack_verification(f):
    from ..payments.consts import PAYSTACK_IPS
    from ..payments.utils import gen_hmac_hash

    @wraps(f)
    def wrapped(*args, **kwargs):
        if 'X-Forwarded-For' in request.headers:
            ip = request.headers.get(
                'X-Forwarded-For',
                request.remote_addr
            ).split(',')[0].strip()
        else:
            ip = request.remote_addr
        if ip not in PAYSTACK_IPS:
            resp = make_response({
                "status": "error",
                "message": "forbidden!"
            }, 403)
            abort(resp)
            logger.info('Unidentifiable client on protected endpoint')

        if 'x-paystack-signature' not in request.headers:
            resp = make_response({
                "status": "error",
                "message": "missing required headers"
            }, 403)
            abort(resp)
            logger.info('Missing header from paystack -- aborted requested')
        else:
            event = json.dumps(request.get_json(force=True), separators=(',', ':'))
            hmac_hash = gen_hmac_hash(event, os.getenv('PAYSTACK_TEST_SECRET'))
            if hmac_hash != request.headers['x-paystack-signature']:
                print("HERE3")
                resp = make_response({
                    "status": "error",
                    "message": "invalid value for required header"
                }, 403)
                logger.info('invalid value for required header')
                abort(resp)
        return f(event, *args, **kwargs)
    return wrapped


def verify_token(token):
    import time
    # try:
    #     uid = auth.verify_id_token(token)['user_id']
    #     return uid
    # except Exception as e:
    #     logger.error("An error occurred while trying to verify token")
    #     logger.error(e)
    #     return None
    try:
        payload = auth.verify_id_token(token)
    except ValueError as err:
        raise Exception(
            "Unable to verify token"
        ) from err
    except (
        ExpiredIdTokenError,
        InvalidIdTokenError,
        RevokedIdTokenError,
    ) as err:
        logger.error("An error occurred while trying to verify token")
        logger.error(err)
        # this happens on localhost all the time.
        str_err = str(err)
        if (str_err.find("Token used too early") > -1):
            times = str_err.split(",")[1]
            times = times.strip().split("<")
            time_ = int(times[1].split('.')[0].strip()) - int(times[0].strip())
            time.sleep(time_)
            return auth.verify_id_token(token)['user_id']
        raise Exception(
            err.default_message
        ) from err
    except CertificateFetchError as err:
        raise Exception(
            "Failed to fetch public key certificates",
        ) from err

    return payload['user_id']


def login_required(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        token = None
        resp = None
        user = None
        excs = (
            ExpiredIdTokenError,
            InvalidIdTokenError,
            RevokedIdTokenError,
        )
        if 'access-token' not in request.headers:
            resp = make_response({
                'status': 'error',
                'msg': 'Missing token'
            }, 403)
            abort(resp)
        try:
            token = request.headers['access-token']
            uid = verify_token(token)
            print(uid)
            logger.debug("user with data: {} still has access".format(uid))
            user = User.query.filter_by(user_id=uid).first()
        except Exception or Exception in excs or auth.ExpiredIdTokenError:
            resp = make_response({
                'msg': 'Expired/Invalid token'
            }, 403)
            abort(resp)
        if not user:
            resp = make_response({
                'status': 'error',
                'msg': 'User with token uid not found'
            }, 404)
            abort(resp)
        return f(user, *args, **kwargs)
    return wrapped
