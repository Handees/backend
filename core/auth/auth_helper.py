from functools import wraps
from models.user_models import Permission, User
from flask import abort, request, make_response
from firebase_admin import auth


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
            uid = auth.verify_id_token(token)
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
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def admin_required(f):
    return permission_required(Permission.ADMIN)(f)
