import os

# Bind to the port Render provides
bind = f"0.0.0.0:{os.environ.get('PORT', '8000')}"

# Worker configuration
workers = 4
worker_class = 'sync'
worker_connections = 1000
timeout = 120

# Logging
accesslog = '-'
errorlog = '-'
loglevel = 'info'