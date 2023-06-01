#!/bin/bash

gcloud builds triggers create github --name="deploy-to-dev" \
    --repo-owner="Handees" --region="europe-west6" \
    --repo-name="backend" --branch-pattern="^development$" \
    --build-config="cloudbuild.yaml"