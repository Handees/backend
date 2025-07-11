#!/bin/bash

# Define the Nginx PID file path
nginx_pid_file="/run/nginx.pid"

# Check if the Nginx PID file exists
if [ -f "$nginx_pid_file" ]; then
  echo "Nginx PID file found. Stopping Nginx..."
  # Use nginx -s stop to gracefully stop Nginx
  if /home/handeesofficial/backend/env/bin/supervisorctl -c supervisord-dev.conf stop nginx; then # Adjust the path to nginx if needed
    echo "Nginx stopped successfully."
  else
    echo "Failed to stop Nginx."
    exit 1 # Exit with an error code
  fi
else
  echo "Nginx PID file not found. Nginx is likely not running."
fi

# Start Nginx
echo "Starting Nginx..."
if /usr/sbin/nginx & sleep 5; then # Adjust the path to nginx if needed
  echo "Nginx started successfully."
else
  echo "Failed to start Nginx."
  exit 1 # Exit with an error code
fi

exit 0 # Exit with success code
