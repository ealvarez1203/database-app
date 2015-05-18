from sqlalchemy import *
from migrate import *


from migrate.changeset import schema
pre_meta = MetaData()
post_meta = MetaData()
requests = Table('requests', post_meta,
    Column('id', Integer, primary_key=True, nullable=False),
    Column('current_user', Integer, nullable=False),
    Column('requestor', Integer, nullable=False),
    Column('request_date', String(length=20), nullable=False),
    Column('return_date', String(length=20), nullable=False),
    Column('project_name', String(length=20), nullable=False),
    Column('location', String(length=20), nullable=False),
    Column('use_detail', String(length=100)),
)


def upgrade(migrate_engine):
    # Upgrade operations go here. Don't create your own engine; bind
    # migrate_engine to your metadata
    pre_meta.bind = migrate_engine
    post_meta.bind = migrate_engine
    post_meta.tables['requests'].create()


def downgrade(migrate_engine):
    # Operations to reverse the above upgrade go here.
    pre_meta.bind = migrate_engine
    post_meta.bind = migrate_engine
    post_meta.tables['requests'].drop()
