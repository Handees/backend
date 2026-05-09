import json
import uuid
import datetime

from sqlalchemy import select, and_
from flask import request, render_template
from loguru import logger

from models.bookings import (
    Booking, BookingCategory, BookingStatusEnum
)
from schemas import (
    BookingSchema,
    UserSchema,
    BlobSchema,
    BookingWorkDaySchema
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
from add_extensions import redis_4, redis_
from . import messages as messages
from schemas.bookings_schema import UploadImagesSchema


logger.remove()
setLogger()


@bookings.post('/')
@login_required
@permission_required(Permission.service_request)
def create_booking(current_user):
    with db.session() as sess:
        data = request.get_json(force=True)
        images = data.pop('images', [])

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
                message=str(e),
                data=schema.error_messages
            )

        new_order.booking_id = uuid4().hex
        new_order.status = BookingStatusEnum.PENDING
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
            images_schema = BlobSchema(uid=current_user.id, many=True)
            images = images_schema.load(to_be_uploaded)
            for img in images:
                img.blob_id = uuid.uuid4().hex

            sess.add_all(images)
        sess.commit()

        data['booking_id'] = new_order.booking_id
        data['images'] = [img.download_url for img in images]
        redis_4.hset(
            'booking_id_to_uid',
            mapping={new_order.booking_id: current_user.user_id}
        )
        data['user'] = UserSchema().dump(current_user)
        data['search_wait_time'] = current_user.calculate_dynamic_request_ttl()
        init_task = pbq(data)
        redis_.set(
            data["booking_id"],
            json.dumps(data),
            ex=data['search_wait_time']
        )

        payload = {
            'task_id': init_task.id,
            'booking': BookingSchema(
                only=('booking_id', 'images')
            ).dump(new_order),
            'search_ttl': data['search_wait_time']
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
            schema=BookingSchema,
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


@bookings.get('/<booking_id>/workingdays')
@login_required
@permission_required(Permission.service_request)
def list_clocks(current_user, booking_id):
    with db.session() as sess:
        stmt = select(Booking).where(
            and_(
                Booking.customer_id == current_user.user_id,
                Booking.booking_id == booking_id
            )
        )
        bk = sess.scalar(stmt)
        if not bk:
            return error_response(
                404,
                "Booking not found, or you didn't request this originally"
            )

        schema = BookingWorkDaySchema(
            many=True,
            only=(
                'booking_id', 'work_sessions', 'id',
                'name', 'date',
            )
        )
        working_days = bk.working_days
        return gen_response(
            200,
            data=schema.dump(working_days)
        )


@bookings.route('/see')
def see():
    return render_template('bookings/index.html')
