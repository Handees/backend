# from redis import StrictRedis
import os
from typing import Optional, Dict

from walrus import *  # noqa: F403
from dotenv import load_dotenv
from flask_sqlalchemy import SQLAlchemy
from passlib.context import CryptContext
from huey import (
    RedisExpireHuey, RedisHuey,
    FileHuey, MemoryHuey, SqliteHuey,
    PriorityRedisExpireHuey, PriorityRedisHuey
)

load_dotenv()


class HueyTemplate:
    _types = {
        'default': RedisHuey,
        'redis': RedisHuey,
        'file': FileHuey,
        'mem': MemoryHuey,
        'priorityh': PriorityRedisHuey,
        'priorityhex': PriorityRedisExpireHuey,
        'redisex': RedisExpireHuey
    }

    def __init__(self, config=None, type_name: Optional[str] = None):
        if config:
            if type_name:
                self.huey = HueyTemplate._types[type_name](**config)
            else:
                self.huey = HueyTemplate._types['default'](**config)
        self.db = SQLAlchemy()

    def get_flask_app(self, config: Optional[Dict] = None):
        from flask import Flask
        app = Flask("huey_app")
        if config:
            app.config.from_object(config)
        self.db.init_app(app)
        return app


class RedCache:
    # class RedisDBEnum(enum.Enum):
    # HUEY_STORE = 0
    # DATA_STORE = 1
    # CATEGORY_GEO_STORE = 2

    def __init__(self, db=1):
        self.client = Walrus(  # noqa: F405
            os.getenv('REDIS_HOST', '127.0.0.1'),
            os.getenv('REDIS_PORT', 6378),
            decode_responses=True,
            password=os.getenv('REDIS_PASS'),
            db=db
        )

    def force_delete(self):
        pass

    # def exists(self, id):
    #     return self.client.exists(id)

    # def delete(self, id):
    #     return self.client.delete(id)

    # def get(self, id):
    #     return self.client.get(id)


pwd_context = CryptContext(schemes=["argon2", "bcrypt"], deprecated="auto")

data_store = redis_ = RedCache().client
customer_pos_store = redis_2 = RedCache(2).client
socket_id_store = redis_4 = RedCache(4).client
cat_geo_store = redis_5 = RedCache(5).client
artisan_cat_geo_store = redis_6 = RedCache(6).client
unmatched_bookings = redis_7 = RedCache(7).client
