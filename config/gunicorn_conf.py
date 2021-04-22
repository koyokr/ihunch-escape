import multiprocessing

name = 'ihunch-escape'
bind = 'unix:/project/ihunch_escape.sock'
workers = 2
keepalive = 32
worker_connections = 512
worker_class = "gevent"
reload = True
loglevel = 'info'
logfile = '-'
spew = False

max_requests = 1000
max_requests_jitter = 50
graceful_timeout = 15
timeout = 15

BASE_DIR = "/project/ihunch_escape"
pythonpath = BASE_DIR
chdir = BASE_DIR

preload_app = False
