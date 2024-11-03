import os
import multiprocessing

# Bind to 0.0.0.0 to listen on all interfaces
bind = f"0.0.0.0:{os.getenv('PORT', '8000')}"

# Number of worker processes
workers = multiprocessing.cpu_count() * 2 + 1

# Maximum number of requests a worker will process before restarting
max_requests = 1000
max_requests_jitter = 50

# Timeout for worker processes (in seconds)
timeout = 120

# Access log format
accesslog = '-'  # Log to stdout
errorlog = '-'   # Log to stderr

# Worker class
worker_class = 'sync'

# Preload application code before worker processes are forked
preload_app = True