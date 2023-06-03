#!/bin/bash

# set env vars
sudo apt-get -y update
sudo apt-get -y install python3 python3-venv python3-dev
sudo apt-get -y install supervisor nginx git

# set up virtual environment
cd /home/handeesofficial/backend
python3 -m venv env
source env/bin/activate

# install dependencies
pip install -r requirements.txt
pip install gunicorn[eventlet]