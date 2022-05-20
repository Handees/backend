import os
from dotenv import load_dotenv

load_dotenv()   # initialize dotenv

base_dir = os.path.abspath(os.getcwd())


class BaseConfig:
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.getenv("app-secret")


class DevConfig(BaseConfig):
    DB_USERNAME = os.getenv('POSTGRES_USER')
    DB_PASSPHRASE = os.getenv('POSTGRES_PASSWORD')
    EXPLAIN_TEMPLATE_LOADINGc = True
    DB_NAME = os.getenv('POSTGRES_DB')
    URI = f"{DB_USERNAME}:{DB_PASSPHRASE}@db/{DB_NAME}"
    SQLALCHEMY_DATABASE_URI = f"postgresql+psycopg2://{URI}"
    CELERY_BACKEND = "db+" + SQLALCHEMY_DATABASE_URI
    CELERY_BROKER_URL = f"amqp://{os.getenv('RABBITMQ_DEFAULT_USER')}:{os.getenv('RABBITMQ_DEFAULT_PASS')}@rabbit"
    # SQLALCHEMY_DATABASE_URI = "sqlite:///base.db"
    DEBUG = True
    ADMIN_EMAIL = os.getenv('ADMIN_EMAIL')


class TestConfig(BaseConfig):
    pass


class Production(BaseConfig):
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")


config_options = {
    "default": DevConfig,
    "development": DevConfig,
    "testing": TestConfig,
    "production": Production
}
