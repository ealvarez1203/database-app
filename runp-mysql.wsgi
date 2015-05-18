#!venv/bin/python

import sys, os
import logging
os.environ['DATABASE_URL'] = 'mysql://user:password@localhost/database_name'

logging.basicConfig(stream=sys.stderr)
sys.path.insert(0,"/var/www/database-app/")

from app import app as application
application.secret_key = 'secret key'
