from redis import StrictRedis
from typing import Optional, Dict
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

    def get_flask_app(self, config: Optional[Dict] = None):
        from flask import Flask

        app = Flask("huey_app")
        if config:
            app.config.from_object(config)

        self.flask_app = app
        return self.flask_app


redis_ = StrictRedis(
    'redis', 6378, charset='utf-8',
    decode_responses=True,
    password=os.getenv('REDIS_PASS'),
    db=1
)
