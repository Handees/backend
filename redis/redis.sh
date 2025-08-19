docker run --name redis -d -p 6379:6379/tcp \
    --restart unless-stopped \
    -v "$(pwd)/redis:/usr/local/etc/redis" \
    redis redis-server /usr/local/etc/redis/redis.conf
