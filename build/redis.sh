DOCKER_BUILDKIT=0 docker build \
    --build-arg REDIS_PASSWORD=$REDIS_PASSWORD \
    --file docker/Dockerfile-redis \
    . -t handees-redis:1.0
