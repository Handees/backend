from . import customer
from flask import request


@customer.route('/')
def sign_up():
    return {
        'msg': "hello"
    }, 200

