import os
import sys
import json
import uuid

from flask import (
    request,
    session
)
from loguru import logger
from firebase_admin import messaging
from flask_socketio import (
    emit,
    join_room,
    ConnectionRefusedError
)
from dotenv import load_dotenv

from utils import (
    LOG_FORMAT, _level, send_notification
)
from models import (
    Artisan, Booking, User,
    ChatMessage, Chat
)
from .utils import (
    error_response,
    update_nearby_count
)
from add_extensions import (
    redis_2,
    redis_,
    redis_4,
    redis_5,
    redis_6,
    redis_7
)
from .. import messages
from core import socketio, db
from core.exc import (
    DataValidationError,
    InvalidBookingTransaction
)
from ..utils import parse_str_data
from ..utils import DistanceAPIClient
from core.api.auth.auth_helper import (
    auth_param_required,
    valid_auth_required
)
from schemas import (
    CoordsSchema,
    BookingAcceptedSchema,
    NewBookingRequestSchema,
    AvailableArtisanLocationSchema
)
from tasks.events import send_event
from models.bookings import categories
from schemas.artisan import ArtisanSchema
from models.bookings import BookingStatusEnum
from core.api.auth.auth_helper import verify_token
from tasks.booking_tasks import update_booking_status
from schemas.bookings_schema import BookingStartSchema
from core.api.bookings.events.utils import parse_event_data


# configure local logger
logger.remove()
logger.add(
    sys.stderr,
    format=LOG_FORMAT,
    colorize=True,
    level=_level
)
load_dotenv()

# create client for distance matrix api
matrix_client = DistanceAPIClient(
    secret=os.getenv('DISTANCE_MATRIX_KEY')
)


@socketio.on('connect', namespace='/chat')
@valid_auth_required
def enter_chat_namespace(uid):
    redis_4.hset(
        "user_to_chat_sid",
        mapping={uid: request.sid}
    )


@socketio.on('join_chat', namespace='/chat')
@parse_event_data
@valid_auth_required
def enter_chat_room(data):
    room = data['booking_id']
    join_room(room)


@socketio.on_error('/artisan')
def default_error_handler(e):
    logger.exception(e)
    socketio.emit(
        'error',
        {'error': str(e)},
        to=request.sid,
        namespace='/artisan'
    )


@socketio.on('connect', namespace='/artisan')
@auth_param_required
def on_connect(auth):
    uid = verify_token(auth['access_token'])
    user: User = User.query.filter_by(user_id=uid).first()
    if not uid:
        raise ConnectionRefusedError
    session['uid'] = uid
    emit('msg', 'welcome!')
    redis_4.set(request.sid, 1)
    redis_4.hset(
        "user_to_sid",
        mapping={uid: request.sid}
    )
    # delete stale connection mapping
    old_sid = redis_4.hget("user_to_sid", uid)
    if old_sid:
        redis_4.hdel("sid_to_user", old_sid)
    redis_4.hset(
        "sid_to_user",
        mapping={request.sid: uid}
    )
    redis_4.hset(
        "user_to_fcm_token",
        mapping={uid: user.mobile_app_registration_token}
    )
    logger.debug('new artisan {} client connection!'.format(request.sid))


@socketio.on('disconnect', namespace='/artisan')
def on_disconnect(reason=None):
    dropping_sid = request.sid
    print(f"==== Disconnecting: {dropping_sid} ====")
    if redis_4.exists(dropping_sid):
        redis_4.delete(dropping_sid)
    # 1. Look up the user associated with this dropping socket
    uid = redis_4.hget("sid_to_user", dropping_sid)
    if uid:
        # 2. Always delete the specific dropping SID from the reverse lookup
        redis_4.hdel("sid_to_user", dropping_sid)
        current_active_sid = redis_4.hget("user_to_sid", uid)
        if current_active_sid == dropping_sid:
            redis_4.hdel("user_to_sid", uid)
            logger.debug(f"User {uid} mapping fully removed.")
        else:
            logger.debug(f"Stale socket {dropping_sid} cleaned. User {uid} remains active on {current_active_sid}.")


@socketio.on('location_update', namespace='/artisan')
@parse_event_data
@valid_auth_required
def update_location(uid, data):
    print("EXECUTING ... for {}".format(uid), flush=True)
    # add coords to redis
    redis_5.geoadd(
        name=data['job_category'],
        values=(data['lon'], data['lat'], uid)
    )

    # add rating to cache
    redis_6.hset("artisan_ratings", uid, data.get('rating', 3.75))
    # room = 'handees_artisan_'+uid
    # join_room(room)
    # # update artisan location on redis
    # psub = redis_2.pubsub(ignore_subscribe_messages=True)
    # psub.unsubscribe('*')

    # redis_5.geoadd(
    #     name=data['job_category'],
    #     values=(data['lon'], data['lat'], uid)
    # )
    # g_hash = redis_5.geohash(
    #     data['job_category'],
    #     uid
    # )
    # g_hash = g_hash[0]
    # # store the count in a g_hash
    # geo_fence_key = g_hash[:5]
    # print(geo_fence_key, "artisan loc ghash")

    # category = data['job_category']
    # cat_hash_key = f'{category}+{geo_fence_key}'
    # prev_cat_hash_key = redis_6.get(uid)

    # if not redis_6.hexists(cat_hash_key, uid):
    #     # in the event that artisan moved away to new geo_fence
    #     # clear previous entry in the previous geo_fence

    #     if prev_cat_hash_key and prev_cat_hash_key != cat_hash_key:
    #         prev = prev_cat_hash_key.split('+')[-1]
    #         update_nearby_count(uid, category, decr=True, prev_hash=prev)

    # if redis_.hexists('ghash_to_artisan_count', geo_fence_key):
    #     if not prev_cat_hash_key:
    #         curr = geo_fence_key
    #         update_nearby_count(uid, category, curr_hash=curr)
    #     elif prev_cat_hash_key and not redis_6.hexists(cat_hash_key, uid):
    #         prev, curr = prev_cat_hash_key.split('+')[-1], geo_fence_key
    #         update_nearby_count(uid, category, prev_hash=prev, curr_hash=curr)
    # else:
    #     _count_store = {}
    #     for cat in categories:
    #         if cat == category:
    #             _count_store[cat] = 1
    #         else:
    #             _count_store[cat] = 0
    #     redis_.hset(
    #         'ghash_to_artisan_count',
    #         geo_fence_key,
    #         str(_count_store)
    #     )

    # redis_6.hset(cat_hash_key, uid, 1)
    # redis_6.set(uid, cat_hash_key)
    # # logger.info(f"The ARTISAN GEOHASH IS:: {g_hash}")

    # # send update to user if artisan is engaged
    # if redis_4.hexists('artisan_to_booking_id', uid):
    #     bk_id = redis_4.hget('artisan_to_booking_id', uid)
    #     print(bk_id)
    #     if redis_7.exists(bk_id):
    #         payload = {
    #             'payload': data,
    #             'recipient': redis_4.hget(
    #                 'booking_id_to_uid',
    #                 bk_id
    #             )
    #         }
    #         send_event('artisan_location_update', payload, '/customer')
    #     else:
    #         # remove stale entry
    #         redis_4.hdel('artisan_to_booking_id', uid)
    # # reduce geohash length to 6 characters
    # # subscribe user to a topic named
    # # after this truncated geohash

    # def handle_updates(msg):
    #     data = parse_str_data(msg['data'])

    #     schema = NewBookingRequestSchema()
    #     customer = data.pop('user')
    #     lat, lon = data.pop('lat'), data.pop('lon')
    #     data = schema.load(
    #         {
    #             **data,
    #             'userDetails': customer,
    #             'coordinates': {
    #                 'lat': lat,
    #                 'lon': lon
    #             }
    #         }
    #     )
    #     socketio.emit(
    #         'new_offer',
    #         data,
    #         to=room,
    #         namespace='/artisan'
    #     )
    #     notification_payload = {
    #         k: json.dumps(v) for k, v in data.items()
    #     }
    #     fcm_token = redis_4.hget("user_to_fcm_token", uid)
    #     send_notification(
    #         notification_payload,
    #         fcm_token,
    #         notification_object={
    #             'body': 'A client near you needs your service',
    #             'title': 'New Service Request Alert! 🚨'
    #         }
    #     )

    # psub.subscribe(**{geo_fence_key: handle_updates})

    # psub.run_in_thread(sleep_time=.01)


@socketio.on('accept_offer', namespace='/artisan')
@parse_event_data
@valid_auth_required
def accept_offer(uid, data):
    """ triggered when artisan accepts offer """
    from tasks.booking_tasks import assign_artisan_to_booking

    room = data['booking_id']
    data['uid'] = uid
    lock_key = f"lock:booking:{room}"
    with redis_.lock(lock_key, ttl=5000):
        if redis_.exists(room):
            # read and remove from queue
            bk_info = parse_str_data(redis_.get(room))
            redis_.delete(room)
            redis_7.set(room, uid)

            # assign artisan to booking
            try:
                assign_artisan_to_booking(data)
            except Exception as e:
                logger.exception(e)
                send_event(
                    'error',
                    error_response(messages.INTERNAL_SERVER_ERROR, uid),
                    '/artisan'
                )
                return

            # send updates to user
            artisan = ArtisanSchema(
                only=(
                    'created_at',
                    'user_profile',
                    'job_category',
                    'jobs_completed',
                    'hourly_rate'
                ),
                exclude=('user_profile.reviews', 'user_profile.rating')
            ).dump(
                Artisan.get_by_user_id(uid)
            )
            lon, lat = redis_5.geopos(
                artisan['job_category'],
                uid
            )[0]
            coords = {'lat': lat, 'lon': lon}
            query = matrix_client.get_route_info(
                source=f"{lat},{lon}",
                destination=f"{bk_info.get('lat')},{bk_info.get('lon')}"
            )
            route_dets = query.json()
            logger.error(route_dets)
            route_dets = route_dets['rows'][0]['elements'][0]
            data = BookingAcceptedSchema().load(
                {
                    'booking_id': data['booking_id'],
                    'artisan_info': artisan,
                    'transit_details': {
                        'time_remaining': float(route_dets['duration']['value']),
                        'coordinates': coords
                    }
                }
            )
            payload = {
                'payload': data,
                'recipient': redis_4.hget(
                    'booking_id_to_uid',
                    room
                )
            }
            try:
                send_event('booking_offer_accepted', payload, '/customer')
                send_event(
                    'offer_matched',
                    {
                        'payload': data,
                        'recipient': redis_4.hget(
                            'booking_id_to_artisan',
                            data['booking_id']
                        )
                    },
                    '/artisan'
                )
            except Exception as e:
                logger.error(e)
                emit('offer_matched', data)
        else:
            payload = {
                'payload': {'msg': messages.BOOKING_CANCELLED, 'data': {}},
                'recipient': uid
            }
            send_event('offer_closed', payload, '/artisan')


@socketio.on('cancel_offer', namespace='/artisan')
@parse_event_data
@valid_auth_required
def cancel_offer_artisan(uid, data):
    """ triggered when artisan cancels offer """
    from schemas.bookings_schema import CancelBookingSchema

    schema = CancelBookingSchema()

    try:
        data = schema.load(data)
    except Exception as e:
        raise DataValidationError(messages.SCHEMA_ERROR, errors=e)
    room = data['booking_id']

    matched_artisan = redis_4.hget('booking_id_to_artisan', room)
    current_artisan = Artisan.get_by_user_id(uid)
    if not redis_.exists(room):
        emit(
            'error',
            error_response(messages.BOOKING_UNAVAILABLE, uid)
        )
        return
    if matched_artisan != current_artisan.user_id:
        emit(
            'error',
            error_response(messages.INVALID_A_CANCEL_OFFER, uid)
        )
        return

    # update status of booking
    try:
        update_booking_status(
            {
                'status': BookingStatusEnum.ARTISAN_CANCELLED,
                **data
            }
        )
    except Exception as e:
        logger.exception(e)
        send_event(
            'error',
            error_response(messages.INTERNAL_SERVER_ERROR, uid),
            '/artisan'
        )

    # remove from queue once canceled
    # TODO: check which dbs are for what
    redis_7.delete(room)
    # remove artisan from booking assignment
    redis_4.hdel('artisan_to_booking_id', uid)

    payload = {
        'payload': messages.dynamic_msg(messages.BOOKING_CANCELLED, "artisan"),
        'recipient': redis_4.hget(
            'booking_id_to_uid',
            room
        )
    }
    send_event(
        'offer_cancelled',
        payload,
        '/customer'
    )


@socketio.on('arrived_location', namespace='/artisan')
@parse_event_data
@valid_auth_required
def handle_location_arrival(uid, data):
    """ triggered when artisan arrives at location """
    room = data['booking_id']
    bk = Booking.query.get(data['booking_id'])

    if bk.status != BookingStatusEnum.ARTISAN_MATCHED:
        emit(
            'error',
            error_response(
                "Invalid action: Cannot carry out"
                " action on booking at this stage",
                uid
            )
        )
        return

    matched_artisan = redis_4.hget('booking_id_to_artisan', room)
    current_artisan = Artisan.get_by_user_id(uid)
    if matched_artisan != current_artisan.user_id:
        emit(
            'error',
            error_response(messages.ARTISAN_NOT_MATCHED_TO_BOOKING, uid)
        )
        return

    # update booking status
    try:
        update_booking_status(
            {
                'status': BookingStatusEnum.ARTISAN_ARRIVED,
                **data
            }
        )
    except Exception as e:
        logger.exception(e)
        send_event(
            'error',
            error_response(messages.INTERNAL_SERVER_ERROR, uid),
            '/artisan'
        )

    payload = {
        'payload': {'message': messages.ARTISAN_ARRIVES},
        'recipient': redis_4.hget(
            'booking_id_to_uid',
            data['booking_id']
        )
    }
    send_event('artisan_arrived', payload, '/customer')

    # stop streaming location to customer
    redis_4.hdel('artisan_to_booking_id', uid)


@socketio.on('start_job', namespace='/artisan')
@parse_event_data
@valid_auth_required
def handle_job_begin(uid, data):
    """ triggered when artisan begins a job """
    with db.session() as sess:
        artisan = Artisan.get_by_user_id(uid)
        bk = Booking.query.get(data['booking_id'])
        if bk.status != BookingStatusEnum.ARTISAN_ARRIVED:
            emit(
                'error',
                error_response(
                    "Invalid action: Cannot carry out",
                    " action on booking at this stage",
                    uid
                )
            )
            return

        room = data['booking_id']

        matched_artisan = redis_4.hget('booking_id_to_artisan', room)
        current_artisan = Artisan.get_by_user_id(uid)
        if matched_artisan != current_artisan.user_id:
            emit(
                'error',
                error_response(messages.ARTISAN_NOT_MATCHED_TO_BOOKING, uid)
            )
            return

        # check if customer has confirmed job
        if not bk.details_confirmed:
            logger.error(InvalidBookingTransaction(
                f"{messages.BOOKING_NOT_CONFIRMED}"
            ))
            emit(
                'error',
                error_response(messages.BOOKING_NOT_CONFIRMED, uid)
            )
            return

        # initiate job
        if bk.artisan.artisan_id == artisan.artisan_id:
            try:
                if not bk.status == BookingStatusEnum.IN_PROGRESS:
                    bk.start_booking(sess)
                    try:
                        sess.commit()
                        payload = {
                            'payload': messages.JOB_STARTED,
                            'recipient': redis_4.hget(
                                'booking_id_to_uid',
                                data['booking_id']
                            )
                        }
                        send_event(
                            'job_started',
                            payload,
                            '/customer'
                        )
                        # send clock-in event
                        payload = {
                            'payload': messages.ARTISAN_CLOCKED_IN,
                            'recipient': redis_4.hget(
                                'booking_id_to_uid',
                                data['booking_id']
                            )
                        }
                        send_event(
                            'artisan_clocked_in',
                            payload,
                            '/customer'
                        )
                    except Exception as e:
                        logger.exception(e)
                        db.session.rollback()
                        send_event(
                            'error',
                            error_response(messages.INTERNAL_SERVER_ERROR, uid),
                            '/artisan'
                        )
                        raise e
                    finally:
                        db.session.close()
            except Exception as e:
                logger.exception(e)
                send_event(
                    'error',
                    error_response(messages.INTERNAL_SERVER_ERROR, uid),
                    '/artisan'
                )
                return
        else:
            logger.error(InvalidBookingTransaction(
                f"Artisan with id {artisan.artisan_id} has not been assigned this order"
            ))
            emit(
                'error',
                error_response(
                    f"Artisan with id {artisan.artisan_id} has "
                    "not been assigned this order",
                    uid
                ),
            )


@socketio.on('job_completed', namespace='/artisan')
@parse_event_data
@valid_auth_required
def handle_job_end(uid, data):
    """ triggered when artisan ends a job """
    from tasks.booking_tasks import job_end

    try:
        data['uid'] = uid
        job_end(data)
        # TODO: remove caches once job_end task completes
        # redis_7.delete(room)
        # redis_4.hdel('artisan_to_booking_id', uid)
    except Exception as e:
        logger.exception(e)
        emit(
            'error',
            error_response(messages.INTERNAL_SERVER_ERROR, uid)
        )
        return


@socketio.on('request_customer_approval', namespace='/artisan')
@parse_event_data
@valid_auth_required
def customer_approval(uid, data):
    """ triggered when artisan specifies initial details of the booking """
    try:
        schema = BookingStartSchema()
        data = schema.load(data)
    except Exception as e:
        logger.error(messages.SCHEMA_ERROR)
        logger.error(e)
        resp = error_response(e.messages, uid)
        emit(
            'error',
            resp
        )
        return {
            'status': 'error',
            'message': messages.SCHEMA_ERROR
        }

    room = data['booking_id']
    matched_artisan = redis_4.hget('booking_id_to_artisan', room)
    current_artisan = Artisan.get_by_user_id(uid)
    if matched_artisan != current_artisan.user_id:
        res = error_response(messages.ARTISAN_NOT_MATCHED_TO_BOOKING, uid)
        emit(
            'error',
            res
        )
        return {
            'status': 'error',
            'message': messages.ARTISAN_NOT_MATCHED_TO_BOOKING
        }

    # inform customer
    payload = {
        'payload': data,
        'recipient': redis_4.hget(
            'booking_id_to_uid',
            data['booking_id']
        )
    }
    send_event('approve_booking_details', payload, '/customer')

    return {
        'status': 'ok',
        'message': 'Sent approval request successfully!'
    }


@socketio.on('message', namespace='/chat')
@valid_auth_required
@parse_event_data
def send_chat_msg(uid, data):
    """sends message to chat room"""
    # check if chat exists in db if not create one
    with db.session() as sess:
        bk_id = data['booking_id']
        print(bk_id)
        new_msg = ChatMessage(**data['chat_object'])
        sid = redis_4.hget('user_to_chat_sid', uid)
        chat_id = redis_4.hget('booking_id_to_chat_id', bk_id)
        if not chat_id:
            new_chat = Chat(booking_id=bk_id)
            sess.add(new_chat)
            chat_id = uuid.uuid4().hex
            new_chat.id = chat_id
            # set in cache
            redis_4.hset('booking_id_to_chat_id', bk_id, chat_id)
        sess.add(new_msg)
        sess.commit()
        room = data['booking_id']
        msg = json.dumps(data['chat_object'])
        socketio.send(msg, to=room, skip_sid=sid, namespace='/chat')


@socketio.on('clock_in', namespace='/artisan')
@parse_event_data
@valid_auth_required
def clock_in(uid, data):
    with db.session() as sess:
        bk = Booking.query.get(data['booking_id'])
        if bk.status != BookingStatusEnum.IN_PROGRESS:
            emit(
                'error',
                error_response(messages.INVALID_CLOCK_IN_ATTEMPT, uid)
            )
            return
        room = data['booking_id']
        matched_artisan = redis_4.hget('booking_id_to_artisan', room)
        current_artisan = Artisan.get_by_user_id(uid)
        if matched_artisan != current_artisan.user_id:
            emit(
                'error',
                error_response(messages.ARTISAN_NOT_MATCHED_TO_BOOKING, uid)
            )
            return
        if bk.clock_in_flag:
            emit(
                'error',
                error_response(
                    "Invalid action: Already clocked! "
                    "Clock-out first",
                    uid
                )
            )
            return
        bk.add_clock_event(sess)
        bk.clock_in_flag = True
        sess.commit()

        # signal customer
        payload = {
            'payload': messages.ARTISAN_CLOCKED_IN,
            'recipient': redis_4.hget(
                'booking_id_to_uid',
                data['booking_id']
            )
        }
        send_event(
            'artisan_clock_in',
            payload,
            '/customer'
        )


@socketio.on('clock_out', namespace='/artisan')
@parse_event_data
@valid_auth_required
def clock_out(uid, data):
    with db.session() as sess:
        bk = Booking.query.get(data['booking_id'])
        if bk.status != BookingStatusEnum.IN_PROGRESS:
            emit(
                'error',
                error_response(messages.INVALID_CLOCK_OUT_ATTEMPT, uid)
            )
            return
        room = data['booking_id']
        matched_artisan = redis_4.hget('booking_id_to_artisan', room)
        current_artisan = Artisan.get_by_user_id(uid)
        if matched_artisan != current_artisan.user_id:
            emit(
                'error',
                error_response(messages.ARTISAN_NOT_MATCHED_TO_BOOKING, uid)
            )
            return
        if not bk.clock_in_flag:
            emit(
                'error',
                error_response(
                    "Invalid action: Can't clock out without "
                    "first clocking in",
                    uid
                )
            )
            return
        bk.add_clock_event(sess, clock_in=False)
        bk.clock_in_flag = False
        sess.commit()
        # signal customer
        payload = {
            'payload': messages.ARTISAN_CLOCKED_OUT,
            'recipient': redis_4.hget(
                'booking_id_to_uid',
                data['booking_id']
            )
        }
        send_event(
            'artisan_clock_out',
            payload,
            '/customer'
        )
