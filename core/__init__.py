# flake8: noqa F403

from flask import Flask
from config import config_options
from .extensions import (
    db, ma, socketio, migrate, cors
)

import logging
from loguru import logger


def configure_logging(app):
    """configure global logging"""
    # Add loguru as logging interceptor
    class InterceptHandler(logging.Handler):
        def emit(self, record):
            try:
                level = logger.level(record.levelname).name
            except ValueError:
                level = record.levelno

            frame, depth = logging.currentframe(), 2
            while frame.f_code.co_filename == logging.__file__:
                frame = frame.f_back
                depth += 1

            logger.opt(depth=depth, exception=record.exc_info).log(
                level, record.getMessage()
            )

    # Register with app
    logging.basicConfig(handlers=[InterceptHandler()], level=0)
    app.logger.addHandler(InterceptHandler())

    # reduce noise from noisy libraries
    logging.getLogger("socketio").setLevel('INFO')


#  app factory
def create_app(config_name):
    app = Flask(__name__)

    # configure application
    app.config.from_object(config_options[config_name])

    # register blueprints
    from .bookings import bookings
    from .payments import payments
    from .ratings import ratings
    from .security import security
    from .user import user

    app.register_blueprint(bookings, url_prefix='/bookings')
    app.register_blueprint(payments, url_prefix='/payments')
    app.register_blueprint(ratings, url_prefix='/ratings')
    app.register_blueprint(security, url_prefix='/security')
    app.register_blueprint(user, url_prefix='/user')

    # link extensions to app instance
    socketio.init_app(app, logger=True, engineio_logger=True, async_mode='eventlet')
    db.init_app(app)
    ma.init_app(app)
    migrate.init_app(app, db)
    cors.init_app(app, resources={r"/*": {"origins": "*"}})
    return app
