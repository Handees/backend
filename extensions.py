# from redis import StrictRedis
from typing import Optional, Dict
from flask_sqlalchemy import SQLAlchemy
from walrus import *  # noqa: F403
import os


class HueyTemplate:
    from huey import (
        RedisExpireHuey, RedisHuey,
        PriorityRedisExpireHuey, PriorityRedisHuey,
        FileHuey, MemoryHuey, SqliteHuey
    )

    _types = {
        'default': RedisHuey,
        'redis': RedisHuey,
        'file': FileHuey,
        'mem': MemoryHuey,
        'priorityh': PriorityRedisHuey,
        'priorityhex': PriorityRedisExpireHuey,
        'redisex': RedisExpireHuey
    }

    def __init__(self, config, type_name: Optional[str] = None):
        if type_name:
            self.huey = HueyTemplate._types[type_name](**config)
        else:
            self.huey = HueyTemplate._types['default'](**config)

    @classmethod
    def get_flask_app(cls, config: Optional[Dict] = None):
        from flask import Flask

        app = Flask("huey_app")
        if config:
            app.config.from_object(config)
        huey_db = SQLAlchemy()
        huey_db.init_app(app)

        return app


class RedCache:
    # class RedisDBEnum(enum.Enum):
    # HUEY_STORE = 0
    # DATA_STORE = 1
    # CATEGORY_GEO_STORE = 2

    def __init__(self, db=1):
        self.client = Walrus(  # noqa: F405
            os.getenv('REDIS_HOST'), 6378, charset='utf-8',
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


data_store = redis_ = RedCache().client
cat_geo_store = redis_2 = RedCache(2).client
