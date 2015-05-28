from sqlalchemy import *
from migrate import *


from migrate.changeset import schema
pre_meta = MetaData()
post_meta = MetaData()
parts = Table('parts', post_meta,
    Column('id', Integer, primary_key=True, nullable=False),
    Column('PO', String(length=50), nullable=False),
    Column('PR', String(length=50), nullable=False),
    Column('part', String(length=20), nullable=False),
    Column('project_name', String(length=30), nullable=False),
    Column('requestor', String(length=30), nullable=False),
    Column('supplier', String(length=50), nullable=False),
    Column('supplier_contact', String(length=50), nullable=False),
    Column('item_description', String(length=200)),
    Column('CPN', String(length=20)),
    Column('PID', String(length=20)),
    Column('manufacturer_part_num', String(length=50)),
    Column('submit_date', String(length=10)),
    Column('tracking', String(length=50)),
    Column('status', String(length=20), nullable=False),
    Column('location', String(length=30)),
    Column('checkout_date', String(length=20)),
    Column('return_date', String(length=20)),
    Column('times_used', Integer, nullable=False),
    Column('current_user', Integer),
    Column('current_project', String(length=30)),
    Column('SN', String(length=30)),
)


def upgrade(migrate_engine):
    # Upgrade operations go here. Don't create your own engine; bind
    # migrate_engine to your metadata
    pre_meta.bind = migrate_engine
    post_meta.bind = migrate_engine
    post_meta.tables['parts'].columns['SN'].create()


def downgrade(migrate_engine):
    # Operations to reverse the above upgrade go here.
    pre_meta.bind = migrate_engine
    post_meta.bind = migrate_engine
    post_meta.tables['parts'].columns['SN'].drop()
