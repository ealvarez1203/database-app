from sqlalchemy import *
from migrate import *


from migrate.changeset import schema
pre_meta = MetaData()
post_meta = MetaData()
history = Table('history', post_meta,
    Column('id', Integer, primary_key=True, nullable=False),
    Column('Part_SN', String),
    Column('project', String, nullable=False),
    Column('user', String, nullable=False),
    Column('checkout_date', String, nullable=False),
    Column('return_date', String, nullable=False),
    Column('detail', String),
)


def upgrade(migrate_engine):
    # Upgrade operations go here. Don't create your own engine; bind
    # migrate_engine to your metadata
    pre_meta.bind = migrate_engine
    post_meta.bind = migrate_engine
    post_meta.tables['history'].columns['detail'].create()


def downgrade(migrate_engine):
    # Operations to reverse the above upgrade go here.
    pre_meta.bind = migrate_engine
    post_meta.bind = migrate_engine
    post_meta.tables['history'].columns['detail'].drop()
