from redis import StrictRedis

redis_ = StrictRedis('redis', 6379, charset='utf-8', decode_responses=True)
