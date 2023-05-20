from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from flask_migrate import Migrate
from flask_socketio import SocketIO
from flask_cors import CORS
# from core.sqlalchemy_ext import RouteSQLAlchemy


db = SQLAlchemy()
ma = Marshmallow()
socketio = SocketIO(
    cors_allowed_origins=[
        'http://127.0.0.1:5020', 'http://127.0.0.1:5500',
        'https://www.piesocket.com'
    ],
    async_mode='eventlet',
    message_queue='redis://redis:6378/2',
    logger=True,
    engineio_logger=True
)
sess = Session()
migrate = Migrate(include_schemas=True)
cors = CORS()
