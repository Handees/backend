import sys

from gevent import monkey
monkey.patch_all()
# ---------------------------------------------------------
# 2. NOW IMPORT HUEY
# Since we patched above, Huey and Redis will load the 
# patched versions of socket/ssl automatically.
# ---------------------------------------------------------
from utils import setLogger
from huey.bin.huey_consumer import consumer_main

setLogger()

if __name__ == '__main__':
    # We reconstruct the command line arguments here.
    # This is equivalent to running:
    # huey_consumer huey_worker.huey -w 2 -n -k greenlet
    
    # Ensure the script name is the first arg (required by consumer_main)
    sys.argv = [
        'huey_consumer',  # Program name
        'tasks.booking_tasks.huey', # Path to your huey instance
        '-w', '2',        # Number of workers
        '-n',             # No periodic tasks (optional, based on your previous cmd)
        '-k', 'greenlet'  # Worker type
    ]

    # Start the worker
    consumer_main()
