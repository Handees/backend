#!/bin/bash

cd /home/handeesofficial/backend
source env/bin/activate

# load config variables
flask load-config-variables

# pre-start actions
flask db upgrade
flask create-categories
flask create-roles

# start nginx
sudo service start nginx

# start workers
source /tmp/APP_ENV.env
env/bin/supervisord -c supervisord-$APP_ENV.conf
