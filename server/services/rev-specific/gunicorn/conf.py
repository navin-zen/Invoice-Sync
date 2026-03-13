"""
Gunicorn config file.
"""

import multiprocessing
import os
import sys

import environ

# /path/to/bookshelf.git/services/rev-specific/gunicorn/conf.py - 4 = /path/to/bookshelf.git
SCRIPT_DIR = environ.Path(__file__) - 1
ROOT_DIR = SCRIPT_DIR - 4
env = environ.Env()  # pylint: disable=invalid-name

if not os.environ.get("DJANGO_SETTINGS_MODULE"):
    print("Please set DJANGO_SETTINGS_MODULE to run the WSGI application", file=sys.stderr)
    sys.exit(1)

DEBUG = env.bool("GST_DJANGO_DEBUG", False)

######################### Server Socket Section #########################
# There is a limit to the length of the socket path name.
# So, we name the file g.sock. This brings the path name under the limit.
# https://gitlab.com/gitlab-org/gitlab-development-kit/issues/55
# bind = 'unix:{}'.format(SCRIPT_DIR('g.sock'))
bind = ["0.0.0.0:{}".format(env.str("GST_NGINX_PORT"))]

######################## Worker Processes Section #######################
# We want 2 workers during DEBUG because some views will request localhost's mock GSTN server
workers = 4 if DEBUG else min(3, 1 + (multiprocessing.cpu_count() * 2))
# Restart worker after 100 requests. Limit the damage of memory leaks
# http://docs.gunicorn.org/en/stable/settings.html#max-requests
max_requests = 100
# The jitter causes the restart per worker to be randomized by randint(0,
# max_requests_jitter)
# http://docs.gunicorn.org/en/stable/settings.html#max-requests-jitter
max_requests_jitter = 10
# If there some really long running request, let it keep running.
# We want to make graceful_timeout as short as possible
# graceful_timeout = 300
# Set timeout to its default value of 30. We will revisit this idea of
# setting timeout=5 later.
# timeout = 5

########################### Debugging Section ###########################
if DEBUG:
    reload = True

######################## Server Mechanics Section #######################
chdir = str(ROOT_DIR)
# pidfile = SCRIPT_DIR('gunicorn.pid')
# Umask sets the default denials
umask = 0o077
pythonpath = str(ROOT_DIR)

########################### Logging Section #############################
accesslog = "-"
if DEBUG:
    access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)d'
else:
    access_log_format = (
        '%({X-Forwarded-For}i)s %(l)s %(u)s %(t)s %({X-Forwarded-Host}i)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)d'
    )
if DEBUG:
    loglevel = "debug"
