#!/bin/bash

source /tmp/APP_ENV.env

curr_env = $APP_ENV

cd /home/handeesofficial/backend
source env/bin/activate

# load config variables
flask load-config-variables

# start nginx
sudo service start nginx

# start workers
sudo supervisord -c supervisord-$curr_env.conf
