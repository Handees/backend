from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from flask_migrate import Migrate
from flask_socketio import SocketIO
from flask_cors import CORS
from flask_session import Session
# from core.sqlalchemy_ext import RouteSQLAlchemy
import os


db = SQLAlchemy()
ma = Marshmallow()

redis_pass = os.getenv('REDIS_PASS')

socketio = SocketIO(
    cors_allowed_origins=[
        'http://127.0.0.1:5020', 'http://127.0.0.1:5500',
        'https://www.piesocket.com'
    ],
    async_mode='eventlet',
    message_queue=f"redis://:{redis_pass}@localhost/2",
    logger=True,
    engineio_logger=True
)
sess = Session()
migrate = Migrate(include_schemas=True)
cors = CORS()
