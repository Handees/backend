#!/bin/bash

gcloud builds triggers create github --name="deploy-to-dev" \
    --repo-owner="Handees" \
    --repo-name="backend" --branch-pattern="^development$" \
    --build-config="cloudbuild.yaml"