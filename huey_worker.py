# run_worker.py
# ---------------------------------------------------------
# 1. PATCH EVERYTHING FIRST
# This must be the very first lines of code. No exceptions.
# ---------------------------------------------------------
from gevent import monkey
monkey.patch_all()

import sys
import os
from tasks.booking_tasks import huey, pbq
# ---------------------------------------------------------
# 2. NOW IMPORT HUEY
# Since we patched above, Huey and Redis will load the 
# patched versions of socket/ssl automatically.
# ---------------------------------------------------------
from huey.bin.huey_consumer import consumer_main

if __name__ == '__main__':
    # We reconstruct the command line arguments here.
    # This is equivalent to running:
    # huey_consumer huey_worker.huey -w 2 -n -k greenlet
    
    # Ensure the script name is the first arg (required by consumer_main)
    sys.argv = [
        'huey_consumer',  # Program name
        'huey_worker.huey', # Path to your huey instance
        '-w', '2',        # Number of workers
        '-n',             # No periodic tasks (optional, based on your previous cmd)
        '-k', 'greenlet'  # Worker type
    ]

    # Start the worker
    consumer_main()
