from flask import Flask

def create_app(config_name):
    app = Flask(__name__)

    # register blueprint
    from .bookings import bookings
    from .payments import payments
    from .ratings import ratings
    from .security import security
    from .user import user

    app.register_blueprint(bookings)
    app.register_blueprint(payments)
    app.register_blueprint(ratings)
    app.register_blueprint(security)
    app.register_blueprint(user)

    return app
