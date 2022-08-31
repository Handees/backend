# flake8: noqa

import unittest
from core import create_app
from models.bookings import (
    db,
    BookingCategory
)
from models.user_models import Role


class BaseTestMixin(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client()

        # create all tables
        print("creating all tables")
        db.create_all()

        # add booking categories
        BookingCategory.create_categories()

        # create user roles
        Role.insert_roles()

        # create dummy data
        resp = self.client.post('/bookings/', json={
            "lat": 6.517871336509268,
            "lon": 3.399740067230001,
            "user_id": "jksdhfuihewuiohio2",
            "job_category": "carpentary"
        })
        unittest.TestLoader.sortTestMethodsUsing = None
        unittest.defaultTestLoader.sortTestMethodsUsing = lambda *args: -1

    def tearDown(self):
        db.session.remove()
        # db.drop_all()
        self.app_context.pop()
