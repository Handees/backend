# flake8: noqa F403

from flask import Flask
from config import config_options
from .extensions import (
    db, ma,
    socketio, migrate,
    cors, sess
)
from utils import error_response

import os
import logging
from loguru import logger
from dotenv import load_dotenv


load_dotenv()


def configure_logging(app: Flask):
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
    default_format = "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> \
        | <cyan>filename={name}</cyan> <cyan>function={function}</cyan> \
            <cyan>line={line}</cyan> msg={message} level={level: <8}"  # noqa

    log_format = "%s elapsedtime={elapsed} {custom_data}" % (default_format)

    logging.basicConfig(handlers=[InterceptHandler()], level=0, format=log_format)


    app.logger.addHandler(InterceptHandler())
    app.logger.__format__ = log_format

    # reduce noise from noisy libraries
    if os.getenv('APP_ENV').lower() not in ('dev', 'development', ):
        pass
    logging.getLogger("urllib3").setLevel('INFO')
    logging.getLogger("cachecontrol").setLevel('INFO')
    logging.getLogger("socketio").setLevel('WARNING')
    logging.getLogger("engineio").setLevel('WARNING')
    logging.getLogger("engineio.server").setLevel('WARNING')
    logging.getLogger("google.auth").setLevel('WARNING')


def config_error_handlers(app):

    @app.errorhandler(404)
    def not_found(error):
        return "Resource/endpoint not found!", 404

    @app.errorhandler(405)
    def method_not_allowed(error):
        return "Method Not Allowed - Soreyeem!", 405

    @app.errorhandler(Exception)
    def all_exception_handler(error):
        # traceback.print_tb(error.__traceback__)
        logger.exception("Uncaught exception received. %s" % str(error))
        return error_response(
            500,
            message="Internal Server error..🤧"
        )


#  app factory
def create_app(config_name):
    app = Flask(__name__)

    # configure application
    app.config.from_object(config_options[config_name])

    # link extensions to app instance
    socketio.init_app(app)
    db.init_app(app)
    ma.init_app(app)
    migrate.init_app(app, db)
    sess.init_app(app)
    cors.init_app(app, resources={r"/*": {"origins": "*"}})

    # register blueprints
    from .api import api
    app.register_blueprint(api)

    # config_error_handlers(app)
    configure_logging(app)
    config_error_handlers(app)

    return app
