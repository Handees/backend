from flask import request, render_template
from loguru import logger

from models.bookings import (
    Booking, BookingCategory,
)
from schemas import (
    BookingSchema,
    ListBookingsSchema,
    UserSchema
)
from models.user_models import Permission
from uuid import uuid4
from . import bookings
from core.api.auth.auth_helper import (
    permission_required,
    login_required
)
from core import db
from utils import (
    error_response,
    gen_response,
    setLogger
)
from tasks.booking_tasks import pbq
from extensions import redis_4
from . import messages as messages
from schemas.bookings_schema import UploadImagesSchema, BookingImageSchema


logger.remove()
setLogger()


@bookings.post('/')
@login_required
@permission_required(Permission.service_request)
def create_booking(current_user):
    with db.session() as sess:
        data = request.get_json(force=True)
        images = data.pop('images', None)

        schema = BookingSchema()
        try:
            new_order: Booking = schema.load(data)
            if images:
                images = UploadImagesSchema().load(images)
        except Exception as e:
            logger.exception(e)
            sess.rollback()
            return error_response(
                400,
                message=schema.error_messages
            )

        new_order.booking_id = uuid4().hex
        category = BookingCategory.get_by_name(data['job_category'])

        if not category:
            sess.rollback()
            return error_response(404, message=messages.dynamic_msg(
                messages.CATEGORY_NOT_FOUND, data['job_category']
            ))
        new_order.booking_category = category
        new_order.user = current_user
        sess.add(new_order)
        sess.flush()

        # add images
        if images:
            _base_img = {
                'user_id': current_user.user_id,
                'booking_id': new_order.booking_id
            }
            to_be_uploaded = [{**_base_img, **img} for img in images['files']]
            images_schema = BookingImageSchema(many=True)
            images = images_schema.load(to_be_uploaded)

            sess.add_all(images)
        sess.commit()

        data['booking_id'] = new_order.booking_id
        redis_4.hset(
            'booking_id_to_uid',
            mapping={new_order.booking_id: current_user.user_id}
        )
        data['user'] = UserSchema().dump(current_user)
        init_task = pbq(data)

        payload = {
            'task_id': init_task.id,
            'booking': BookingSchema(only=('booking_id', 'images')).dump(new_order)
        }

        return gen_response(
            201,
            payload,
            message=messages.BOOKING_MADE
        )


@bookings.get('/')
@login_required
@permission_required(Permission.service_request)
def view_bookings(current_user):
    with db.session():
        bookings = Booking.query.filter_by(
            customer_id=current_user.user_id
        ).all()

        return gen_response(
            200,
            bookings,
            schema=ListBookingsSchema,
            many=True
        )


@bookings.get('/<booking_id>')
@login_required
@permission_required(Permission.service_request)
def fetch_booking_details(current_user, booking_id):
    booking = Booking.query.get(booking_id)
    if not booking:
        return error_response(
            404,
            message=f'booking with id {booking_id} not found'
        )

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


@bookings.post('<booking_id>/upload')
@login_required
@permission_required(Permission.service_request)
def request_presigned_urls(current_user, booking_id):
    _base_img = {
        'user_id': current_user.user_id,
        'booking_id': booking_id
    }
    with db.session() as sess:
        data = request.get_json(force=True)
        try:
            images = UploadImagesSchema().load(data)
        except Exception as e:
            return error_response(
                status_code=400,
                message=str(e)
            )
        to_be_uploaded = [{**_base_img, **img} for img in images['files']]
        images_schema = BookingImageSchema(many=True)
        images = images_schema.load(to_be_uploaded)

        sess.add_all(images)
        sess.commit()

        resp = BookingImageSchema(
            many=True,
            only=('filename', 'url')
        ).dump(images)
        return gen_response(
            200,
            data=resp
        )


@bookings.route('/see')
def see():
    return render_template('bookings/index.html')
