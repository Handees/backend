#!/usr/bin/bash

set -a
source <(sed 's/\r$//' .env)
set +a

gcloud builds submit . \
    --config=build/cloudbuild.yaml \
    --substitutions="_DB_CERT_PATH=$DATABASE_CERT_PATH,_DB_CERT_DIR_PATH=$DATABASE_CERT_DIR_PATH,_COCKROACH_DB_CERT_URL=$COCKROACH_DB_CERT_URL"
