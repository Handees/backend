#!/bin/bash

celery -A celery_worker.celery worker -l DEBUG