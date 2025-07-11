# #!/bin/bash

if /home/handeesofficial/backend/env/bin/supervisord -c supervisord-dev.conf & sleep 5; then # Adjust the path to nginx if needed
    echo "Supervisord started successfully."
    if /home/handeesofficial/backend/env/bin/supervisorctl -c supervisord-dev.conf start nginx; then
        echo "started Nginx successfully"
        exit 0
    else
        echo "Failed to nginx"
        exit 1
    fi
else
    echo "Failed to start supervisord."
    exit 1 # Exit with an error code
fi
