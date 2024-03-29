import os
from dotenv import load_dotenv
import redis

load_dotenv()   # initialize dotenv

base_dir = os.path.abspath(os.getcwd())


class BaseConfig:
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.getenv("APP_SECRET")
    REDIS_PORT = os.getenv('REDIS_PORT', 6378)
    REDIS_HOST = os.getenv('REDIS_HOST', '127.0.0.1')
    REDIS_PASS = os.getenv('REDIS_PASS')
    HUEY_CONFIG = dict(
        connection_pool=redis.ConnectionPool(
            host=REDIS_HOST, port=REDIS_PORT,
            password=REDIS_PASS, db=0
        )
    )
    ADMIN_EMAIL = os.getenv('ADMIN_EMAIL')
    DB_USERNAME = os.getenv('DATABASE_USER')
    DB_PASSPHRASE = os.getenv('DATABASE_PASSWORD')
    F_KEY_PATH = os.path.join(
        os.path.abspath(os.getcwd()),
        os.getenv('F_KEY')
    )
    SQLALCHEMY_ECHO = False
    SESSION_TYPE = 'redis'


class DevConfig(BaseConfig):
    DB_NAME = f"{os.getenv('DATABASE_HOST')}/{os.getenv('DATABASE_NAME')}"
    URI = f"{BaseConfig.DB_USERNAME}:{BaseConfig.DB_PASSPHRASE}@{DB_NAME}"
    SQLALCHEMY_DATABASE_URI = f"postgresql+psycopg2://{URI}"
    FLASK_COVERAGE = True
    SESSION_REDIS = redis.Redis(
        host=BaseConfig.REDIS_HOST,
        port=BaseConfig.REDIS_PORT,
        password=BaseConfig.REDIS_PASS,
        db=5
    )


class StagingConfig(BaseConfig):
    DB_NAME = f"{os.getenv('DATABASE_HOST')}/{os.getenv('DATABASE_NAME')}"
    DEBUG = True
    URI = f"{BaseConfig.DB_USERNAME}:{BaseConfig.DB_PASSPHRASE}@{DB_NAME}"
    SQLALCHEMY_DATABASE_URI = f"postgresql+psycopg2://{URI}"
    FLASK_COVERAGE = True
    SESSION_REDIS = redis.Redis(
        host=BaseConfig.REDIS_HOST,
        port=BaseConfig.REDIS_PORT,
        password=BaseConfig.REDIS_PASS,
        db=5
    )


class TestConfig(BaseConfig):
    DB_NAME = os.getenv('TEST_DB', 'handeestestdb')
    URI = f"{BaseConfig.DB_USERNAME}:{BaseConfig.DB_PASSPHRASE}@{DB_NAME}"
    SQLALCHEMY_DATABASE_URI = f"postgresql+psycopg2://{URI}"
    ADMIN_EMAIL = os.getenv('ADMIN-EMAIL')
    TESTING = True
    FLASK_COVERAGE = True


class Production(BaseConfig):
    DB_NAME = os.getenv('DATABASE-URL')
    URI = f"{BaseConfig.DB_USERNAME}:{BaseConfig.DB_PASSPHRASE}@{DB_NAME}"
    SQLALCHEMY_DATABASE_URI = f"postgresql+psycopg2://{URI}"


config_options = {
    "default": TestConfig,
    "local": StagingConfig,
    "staging": StagingConfig,
    "development": DevConfig,
    "dev": DevConfig,
    "testing": TestConfig,
    "production": Production
}
