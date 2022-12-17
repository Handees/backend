# flake8: noqa F403

from flask import Flask
from config import config_options
from .extensions import (
    db, ma,
    socketio, migrate,
    cors
)
from .utils import error_response

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
    logging.getLogger("socketio").setLevel('ERROR')

    @app.errorhandler(404)
    def not_found(error):
        return "Resource/endpoint not found!", 404
    
    @app.errorhandler(405)
    def not_found(error):
        return "Method Not Allowed - Soreyeem!", 405

    @app.errorhandler(Exception)
    def all_exception_handler(error):
        # traceback.print_tb(error.__traceback__)
        logger.exception("Uncaught exception received. %s" % str(error))
        return error_response(
            500,
            message="Internal Server error..🤧"
        )


# def config_error_handlers(app):

#     @app.errorhandler(Exception)
#     def all_exception_handler(error):
#         # traceback.print_tb(error.__traceback__)
#         logger.exception("Uncaught exception received. %s" % str(error))
#         return error_response(
#             500,
#             message="An error occurred on the server"
#         )


#  app factory
def create_app(config_name):
    app = Flask(__name__)

    # configure application
    app.config.from_object(config_options[config_name])

    # register blueprints
    from .api import api

    app.register_blueprint(api)

    # link extensions to app instance
    socketio.init_app(app, logger=True, engineio_logger=True)
    db.init_app(app)
    ma.init_app(app)
    migrate.init_app(app, db)
    cors.init_app(app, resources={r"/*": {"origins": "*"}})

    # config_error_handlers(app)
    configure_logging(app)

    return app
