#!/bin/sh

DOCKER_BUILDKIT=0 docker build \
    --build-arg DATABASE_CERT_PATH=$DATABASE_CERT_PATH \
    --build-arg DATABASE_CERT_DIR_PATH=$DATABASE_CERT_DIR_PATH \
    --build-arg COCKROACH_DB_CERT_URL=$COCKROACH_DB_CERT_URL \
    --file docker/Dockerfile \
    . -t handees-backend:1.1
