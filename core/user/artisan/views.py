from . import artisan
from flask import request


@artisan.post('/')

def add_new_artisan(user_id):
    pass
