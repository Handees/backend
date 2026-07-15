import os
import sys
import redis

from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from flask_migrate import Migrate
from flask_socketio import SocketIO
from flask_cors import CORS
from flask_session import Session
from dotenv import load_dotenv


load_dotenv()

db = SQLAlchemy()
ma = Marshmallow()

redis_pass = os.getenv('REDIS_PASS')
redis_port = os.getenv('REDIS_PORT', 6378)


# Force a raw connection test
try:
    print("Testing raw Redis connection from Cloud Run...", file=sys.stderr)
    redis_url = f"redis://:{redis_pass}@{os.getenv('REDIS_HOST')}:{redis_port}"
    test_client = redis.from_url(redis_url, socket_connect_timeout=3)
    test_client.ping()
    print("SUCCESS: Cloud Run can see Redis!", file=sys.stderr)
except Exception as e:
    print(f"FATAL REDIS ERROR: {str(e)}", file=sys.stderr)

socketio: SocketIO = SocketIO(
    cors_allowed_origins=[
        'http://127.0.0.1:5020',
        'https://www.piesocket.com',
        'http://127.0.0.1:5501'
    ],
    async_mode='gevent',
    message_queue=f"redis://:{redis_pass}@{os.getenv('REDIS_HOST')}:{redis_port}/7",
    logger=True,
    engineio_logger=True
)
sess = Session()
migrate = Migrate(include_schemas=True)
cors = CORS()


def init_app(app):
    socketio.init_app(app)
    db.init_app(app)
    ma.init_app(app)
    migrate.init_app(app, db)
    sess.init_app(app)
    cors.init_app(app, resources={r"/*": {"origins": ['http://127.0.0.1:5501']}})
