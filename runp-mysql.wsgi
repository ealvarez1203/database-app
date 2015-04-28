#!venv/bin/python

import sys, os
import logging
os.environ['DATABASE_URL'] = 'mysql://apps:apps@localhost/apps'

logging.basicConfig(stream=sys.stderr)
sys.path.insert(0,"/var/www/database-app/")

from app import app as application
application.secret_key = 'l\xa4\x05H%\xf4\xf51\x8dh\xdf\xd5(\x9d\xc1e\xc2\xe7W\xc8v-\xdf\xa9'