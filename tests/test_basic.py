from flask import current_app
from tests.base import BaseTestMixin


class BasicsTestCase(BaseTestMixin):

    def test_app_exists(self):
        self.assertFalse(current_app is None)

    def test_app_is_testing(self):
        self.assertTrue(current_app.config['TESTING'])
