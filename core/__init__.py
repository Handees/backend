from flask import Flask
from config import config_options, DevConfig
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from flask_migrate import Migrate
from flask_socketio import SocketIO
from celery import Celery
from flask_cors import CORS

# instantiate extensions
db, ma = SQLAlchemy(), Marshmallow()
socketio = SocketIO()
migrate = Migrate(include_schemas=True)
celery = Celery(__name__, broker=DevConfig.CELERY_BROKER_URL)
cors = CORS()


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
    app.register_blueprint(payments)
    app.register_blueprint(ratings)
    app.register_blueprint(security)
    app.register_blueprint(user)

    # link extensions to app instance
    socketio.init_app(app, logger=True, engineio_logger=True)
    db.init_app(app)
    ma.init_app(app)
    migrate.init_app(app, db)
    celery.conf.update(app.config)
    celery.autodiscover_tasks()
    cors.init_app(app)
    return app
