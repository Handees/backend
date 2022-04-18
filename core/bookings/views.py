from flask import request
from models.bookings import Booking
from models.user_models import Permission
from . import bookings
from core.auth.auth_helper import permission_required, login_required
from core import db


@bookings.route('/', methods=['POST'])
@login_required
@permission_required(Permission.service_request)
def create_booking(current_user):
    data = request.get_json(force=True)
    new_order = Booking(params=data)
    db.session.add(new_order)
    db.session.commit()
    return {
        'status': 'success',
        'msg': 'booking created successfully'
    }
