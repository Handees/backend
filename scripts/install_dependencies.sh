#!/bin/bash

# set env vars
source /tmp/APP_ENV.env

echo "$APP_ENV"

sudo apt-get -y update
sudo apt-get -y install python3 python3-venv python3-dev
sudo apt-get -y install nginx git

# set up virtual environment
cd /home/handeesofficial/backend
python3 -m venv env
source env/bin/activate

# install dependencies
pip install -r requirements.txt
pip install supervisor
pip install eventlet==0.33.0 https://github.com/benoitc/gunicorn/archive/refs/heads/master.zip#egg=gunicorn==20.1.0
pip install gunicorn==20.1.0
