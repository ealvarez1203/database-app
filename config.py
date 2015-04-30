import os
basedir = os.path.abspath(os.path.dirname(__file__))

SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'savbu-database.db')
SQLALCHEMY_MIGRATE_REPO = os.path.join(basedir, 'db_repository')
WTF_CSRF_ENABLED = True
SECRET_KEY = 'Your Secret Key'
UPLOAD_FOLDER = os.path.join(basedir, 'tmp')
ALLOWED_EXTENSIONS = set(['xlsx', 'xlsm', 'xls'])

# mail server settings
MAIL_SERVER = 'smtp.gmail.com'
MAIL_PORT = 465
MAIL_USE_TLS = False
MAIL_USE_SSL = True
MAIL_USERNAME = 'eduardoalvarez1203@gmail.com'
MAIL_PASSWORD = 'edualv03'

# administrator list
ADMINS = ['eduardoalvarez1203@gmail.com']

