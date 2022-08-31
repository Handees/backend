# flake8: noqa

from .address import (
    Address, Addresstypes
)
from .user_models import User, Role, Artisan
from .base import BaseModelPR, TimestampMixin
from .bookings import Booking, BookingCategory, BookingCategory
from .documents import Document, Document_category
from .location import Landmark, City
from .payments import Payment
from .ratings import Rating
