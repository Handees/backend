from flask import request
from . import user
from core import db
from models.user_models import User
from sqlalchemy.exc import IntegrityError


@user.route('/', methods=['POST'])
def register():
    data = request.get_json(force=True)
    new_user = User(params=data)
    db.session.add(new_user)
    try:
        db.session.commit()
        return {
            'status': 'success',
            'msg': 'user created successfully'
        }, 201
    except IntegrityError:
        return {
            'status': 'error',
            'msg': f"user with id {data['user_id']} already exists",
        }, 400
