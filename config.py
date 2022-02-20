import os
from dotenv import load_dotenv

load_dotenv()   # initialize dotenv

base_dir = os.path.abspath(os.getcwd())

class BaseConfig:
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.getenv("app-secret")

class DevConfig(BaseConfig):
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{base_dir}/dev.sqlite" # sqlite3 for dev environment
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
