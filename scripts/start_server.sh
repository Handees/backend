#!/bin/bash

cd /home/handeesofficial/backend
source env/bin/activate

# load config variables
flask load-config-variables

# start nginx
sudo service start nginx

# start workers
source /tmp/APP_ENV.env
sudo supervisord -c supervisord-$APP_ENV.conf
