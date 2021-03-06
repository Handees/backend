from flask import request, render_template
from models.bookings import Booking
from models.user_models import Permission
from . import bookings
from ..auth.auth_helper import permission_required, login_required
from .. import db
from tasks.push_booking_to_queue import pbq
import uuid


@bookings.route('/', methods=['POST'])
# @login_required
# @permission_required(Permission.service_request)
def create_booking():
    data = request.get_json(force=True)
    data['booking_id'] = str(uuid.uuid4())
    print(data)
    new_order = Booking(params=data)
    print(new_order)
    db.session.add(new_order)
    db.session.commit()
    data['booking_id'] = new_order.booking_id
    init_task = pbq(data)
    return {
        'status': 'success',
        'msg': 'booking created successfully',
        'data': {
            'task_id': init_task.id,
            'booking_id': new_order.booking_id
        }
    }


@bookings.route('/see')
def see():
    return render_template('bookings/index.html')
