from flask import Flask
from config import config_options
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from flask_migrate import Migrate

# instantiate extensions
db, ma = SQLAlchemy(), Marshmallow()
migrate = Migrate(include_schemas=True)


#  app factory
def create_app(config_name):
    app = Flask(__name__)

    # configure application
    app.config.from_object(config_options[config_name])

    # link extensions to app instance
    db.init_app(app)
    ma.init_app(app)
    migrate.init_app(app, db)

    # register blueprints
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

    # # create date dimension
    # conn = op.get_bind()
    # file_ = open('models/date_dim.sql')
    # escaped_sql = sa.text(file_.read())
    # conn.execute(escaped_sql)

    return app
