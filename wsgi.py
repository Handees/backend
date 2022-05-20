# flake8: noqa

from json import load
from core import create_app, socketio
from dotenv import load_dotenv
from models.user_models import *
from models.base import *
from models.documents import *
from models.address import *
from models.bookings import *
from models.ratings import *
from models.location import *
from models.payments import *
from models.utils import *
import os


load_dotenv()

app = create_app(os.getenv('FLASK_CONFIG') or 'default')


@app.shell_context_processor
def make_shell_context():
    return dict(app=app, role=Role)


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000)
    # socketio.run(app)
