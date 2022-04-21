from flask import request
from models.bookings import Booking
from models.user_models import Permission
from . import bookings
from core.auth.auth_helper import permission_required, login_required
from core import db
from tasks import push_booking_to_queue


@bookings.route('/', methods=['POST'])
@login_required
@permission_required(Permission.service_request)
def create_booking(current_user):
    data = request.get_json(force=True)
    init_task = push_booking_to_queue.delay(data)
    new_order = Booking(params=data)
    db.session.add(new_order)
    db.session.commit()
    return {
        'status': 'success',
        'msg': 'booking created successfully',
        'data': {
            'task_id': init_task.id
        }
    }


# @bookings.route('/see')
# def see():
#     return {
#         'data': current_app.config['CELERY_BROKER_URL'],
#         'm': current_app.config['CELERY_BACKEND']
#     }
