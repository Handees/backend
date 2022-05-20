#!/usr/bin/env python

# flake8: noqa

import os
from core import create_app

app = create_app(os.getenv('FLASK_CONFIG') or 'default')
app.app_context().push()

from core import celery