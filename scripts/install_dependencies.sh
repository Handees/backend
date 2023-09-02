#!/bin/bash

# set env vars
source /tmp/APP_ENV.env

echo "$APP_ENV"

sudo apt-get -y update
sudo apt-get -y install python3 python3-venv python3-dev
sudo apt-get -y install nginx git

git clone https://github.com/curiouspaul1/prembly_python

# set up virtual environment
cd /home/handeesofficial/backend
python3 -m venv env
source env/bin/activate

# install dependencies
pip install -r requirements.txt
pip install supervisor

# eventlet
# https://github.com/eventlet/eventlet/issues/702
# https://stackoverflow.com/questions/75137717/eventlet-dns-python-attribute-error-module-dns-rdtypes-has-no-attribute-any
pip uninstall eventlet
pip install eventlet==0.33.3

# gunicorn
pip install gunicorn

# install prembly
cd /home/handeesofficial/prembly_python
python3 setup.py install
