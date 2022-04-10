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
    DB_NAME = os.getenv('POSTGRES_DB')
    URI = f"{DB_USERNAME}:{DB_PASSPHRASE}@db/{DB_NAME}"
    SQLALCHEMY_DATABASE_URI = f"postgresql+psycopg2://{URI}"
    DEBUG = True


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
