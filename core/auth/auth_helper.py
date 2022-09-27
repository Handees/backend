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
from loguru import logger


def login_required(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        token = None
        resp = None
        if 'access-token' not in request.headers:
            resp = make_response({
                'status': 'error',
                'msg': 'Missing token'
            }, 403)
            abort(resp)
        try:
            token = request.headers['access-token']
            uid = auth.verify_id_token(token)['user_id']
            print(uid)
            logger.debug("user with data: {} still has access".format(uid))
            user = User.query.filter_by(user_id=uid).first()
            if not user:
                resp = make_response({
                    'status': 'error',
                    'msg': 'User with token uid not found'
                }, 404)
                abort(resp)
            return f(user, *args, **kwargs)
        except auth.ExpiredIdTokenError:
            resp = make_response({
                'msg': 'Expired token'
            }, 403)
            abort(resp)
    return wrapped


def permission_required(permission):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not args[0].can(permission):
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
            if not args[0].role == Role.get_by_name(role):
                resp = make_response(
                    {
                        'status': 'error',
                        'msg': 'user cannot perform this action'
                    },
                    403
                )
                abort(resp)
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def admin_required(f):
    return permission_required(Permission.ADMIN)(f)
