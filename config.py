import os
from dotenv import load_dotenv
import redis

load_dotenv()   # initialize dotenv

base_dir = os.path.abspath(os.getcwd())


class BaseConfig:
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.getenv("app_secret")
    HUEY_CONFIG = dict(
        connection_pool=redis.ConnectionPool(
            host=os.getenv('REDIS_HOST') or 'redis', port=6378,
            password=os.getenv('REDIS_PASS'), db=0
        )
    )
    ADMIN_EMAIL = os.getenv('ADMIN_EMAIL')
    DB_USERNAME = os.getenv('POSTGRES_USER')
    DB_PASSPHRASE = os.getenv('POSTGRES_PASSWORD')
    F_KEY_PATH = os.path.join(
        os.path.abspath(os.getcwd()),
        os.getenv('F_KEY')
    )


class DevConfig(BaseConfig):
    DB_NAME = os.getenv('POSTGRES_DB')
    EXPLAIN_TEMPLATE_LOADING = True
    DEBUG = True
    URI = f"{BaseConfig.DB_USERNAME}:{BaseConfig.DB_PASSPHRASE}@localhost:5432/{DB_NAME}"
    SQLALCHEMY_DATABASE_URI = f"postgresql+psycopg2://{URI}"
    FLASK_COVERAGE = True


class StagingConfig(BaseConfig):
    DB_NAME = os.getenv('POSTGRES_DB')
    URI = f"{BaseConfig.DB_USERNAME}:{BaseConfig.DB_PASSPHRASE}@db/{DB_NAME}"
    SQLALCHEMY_DATABASE_URI = f"postgresql+psycopg2://{URI}"
    FLASK_COVERAGE = True


class TestConfig(BaseConfig):
    DB_NAME = os.getenv('TEST_DB', 'handeestestdb')
    URI = f"{BaseConfig.DB_USERNAME}:{BaseConfig.DB_PASSPHRASE}@localhost:5434/{DB_NAME}"
    SQLALCHEMY_DATABASE_URI = f"postgresql+psycopg2://{URI}"
    ADMIN_EMAIL = os.getenv('ADMIN_EMAIL')
    TESTING = True
    FLASK_COVERAGE = True


class Production(BaseConfig):
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")


config_options = {
    "default": TestConfig,
    "staging": StagingConfig,
    "development": DevConfig,
    "testing": TestConfig,
    "production": Production
}
