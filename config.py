import os
from dotenv import load_dotenv

load_dotenv()   # initialize dotenv

base_dir = os.path.abspath(os.getcwd())


class BaseConfig:
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.getenv("app-secret")


class DevConfig(BaseConfig):
    DB_USERNAME = os.getenv('DB_USERNAME')
    DB_PASSPHRASE = os.getenv('DB_PASSPHRASE')
    DB_NAME = os.getenv('DB_NAME')
    URI = f"{DB_PASSPHRASE}:{DB_PASSPHRASE}@localhost/{DB_NAME}"
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
