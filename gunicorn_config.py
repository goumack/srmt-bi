# SRMT Business Intelligence - Gunicorn Production Configuration

import multiprocessing
import os

# Server socket
bind = f"{os.getenv('HOST', '0.0.0.0')}:{os.getenv('PORT', '5000')}"
backlog = 2048

# Worker processes
workers = int(os.getenv('MAX_WORKERS', multiprocessing.cpu_count() * 2 + 1))
worker_class = "gevent"
worker_connections = 1000
max_requests = 10000
max_requests_jitter = 1000
preload_app = True
timeout = 30
keepalive = 2

# Logging
accesslog = "-"
errorlog = "-"
loglevel = os.getenv('LOG_LEVEL', 'info').lower()
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = 'srmt_bi_production'

# SSL (if needed)
# keyfile = '/path/to/keyfile'
# certfile = '/path/to/certfile'

# Security
limit_request_line = 4096
limit_request_fields = 100
limit_request_field_size = 8190

# Performance tuning
preload_app = True
max_requests = 1000
max_requests_jitter = 100

# Graceful restarts
graceful_timeout = 30
timeout = 30

def post_fork(server, worker):
    """Called just after a worker has been forked."""
    server.log.info("Worker spawned (pid: %s)", worker.pid)

def pre_fork(server, worker):
    """Called just prior to forking the worker subprocess."""
    pass

def when_ready(server):
    """Called just after the server is started."""
    server.log.info("SRMT BI Production server is ready. Listening at: %s", server.address)

def worker_int(worker):
    """Called just after a worker exited on SIGINT or SIGQUIT."""
    worker.log.info("worker received INT or QUIT signal")

def on_exit(server):
    """Called just before exiting Gunicorn."""
    server.log.info("SRMT BI Production server is shutting down.")