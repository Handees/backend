from flask import request

from . import ratings
from core.api.auth.auth_helper import login_required


@ratings.post('/')
@login_required
def add_rating(current_user):
    pass
