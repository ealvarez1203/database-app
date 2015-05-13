from flask import Flask 
from flask.ext.sqlalchemy import SQLAlchemy 
from flask.ext.bcrypt import Bcrypt
from flask.ext.login import LoginManager
from flask.ext.mail import Mail 
import logging

app = Flask(__name__)
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
mail = Mail(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

app.config.from_object('config')

activity_log = logging.FileHandler('tmp/database-activity.log')
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
activity_log.setFormatter(formatter)
app.logger.addHandler(activity_log)
activity_log.setLevel(logging.INFO)

from app import views, models

# mail error service
from config import basedir, ADMINS, MAIL_SERVER, MAIL_PORT, MAIL_USERNAME, MAIL_PASSWORD

if not app.debug:
    #import logging
    from logging.handlers import SMTPHandler
    credentials = None
    if MAIL_USERNAME or MAIL_PASSWORD:
        credentials = (MAIL_USERNAME, MAIL_PASSWORD)
    mail_handler = SMTPHandler((MAIL_SERVER, MAIL_PORT), 'no-reply@' + MAIL_SERVER, ADMINS, 'savbu-database failure', credentials)
    mail_handler.setLevel(logging.ERROR)
    app.logger.addHandler(mail_handler)

# log file error 
if not app.debug:
    #import logging
    from logging.handlers import RotatingFileHandler
    file_handler = RotatingFileHandler('tmp/savbu-inventory.log', 'a', 1 * 1024 * 1024, 10)
    file_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
    app.logger.setLevel(logging.INFO)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.info('savbu-inventory startup')