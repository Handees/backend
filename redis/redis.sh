#!/bin/bash

docker run --name redis -d -p 6379:6379/tcp --restart unless-stopped -v /c/users/owner/documents/projects/backend/redis:/usr/local/etc/redis --name redis redis redis-server /usr/local/etc/redis/redis.conf
