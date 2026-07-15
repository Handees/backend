#!/usr/bin/bash

# Move explicitly into the directory where this script actually lives
# cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"

# Parse the local .env safely to get REDIS_PASSWORD
set -a
source <(sed 's/\r$//' .env)
set +a

# Jump back up to the project root so gcloud context resolves correctly
# cd ..

# Submit explicitly targeting the Redis yaml config
gcloud builds submit . \
    --config="build/cloudbuild-redis.yaml" \
    --substitutions="_REDIS_PASSWORD=$REDIS_PASS"
