from flask import request, render_template
from loguru import logger

from models.bookings import Booking, BookingCategory
from schemas.bookings_schema import BookingSchema
from models.user_models import Permission
from uuid import uuid4
from . import bookings
from core.api.auth.auth_helper import (
    permission_required,
    login_required
)
from core import db
from core.utils import (
    error_response,
    gen_response,
    setLogger
)
from tasks.booking_tasks import pbq
from extensions import redis_4
from . import messages as messages


logger.remove()
setLogger()


@bookings.post('/')
@login_required
@permission_required(Permission.service_request)
def create_booking(current_user):
    data = request.get_json(force=True)

    schema = BookingSchema()
    try:
        new_order = schema.load(data)
    except Exception:
        db.session.rollback()
        return error_response(
            400,
            message=schema.error_messages
        )

    new_order.booking_id = uuid4().hex
    category = BookingCategory.get_by_name(data['job_category'])

    if not category:
        db.session.rollback()
        return error_response(404, message=messages.dynamic_msg(
            messages.CATEGORY_NOT_FOUND, data['job_category']
        ))
    new_order.booking_category = category
    new_order.user = current_user
    db.session.add(new_order)
    db.session.commit()

    data['booking_id'] = new_order.booking_id
    redis_4.hset(
        'booking_id_to_uid',
        mapping={new_order.booking_id: current_user.user_id}
    )
    init_task = pbq(data)

    payload = {
        'task_id': init_task.id,
        'booking_id': new_order.booking_id
    }

    return gen_response(
        201,
        payload,
        message=messages.BOOKING_MADE
    )


@bookings.get('/<booking_id>')
@login_required
@permission_required(Permission.service_request)
def fetch_booking_details(current_user, booking_id):
    booking = Booking.query.get(booking_id)
    if not booking:
        return error_response(404, message=f'booking with id {booking_id} not found')

    return gen_response(200, booking, schema=BookingSchema)


@bookings.delete('/<booking_id>')
@login_required
@permission_required(Permission.service_request)
def delete_booking(current_user, booking_id):
    booking = Booking.query.get(booking_id)
    if not booking:
        return error_response(404, message=f'booking with id {booking_id} not found')

    # delete booking resource
    db.session.delete(booking)
    db.session.commit()

    msg = f'Deleted booking with id {booking_id}'

    return gen_response(200, message=msg)


@bookings.route('/see')
def see():
    return render_template('bookings/index.html')
