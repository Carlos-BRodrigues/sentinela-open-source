from alchemy import Entity, Message, Sentinel, Media, Reaction, Comment
from alchemy import Base
from json import load
from sqlalchemy.orm import sessionmaker

from sqlalchemy import create_engine
from sqlalchemy.engine.url import URL

with open("config.json") as jsonfile:
    db_config = load(jsonfile)['database']

engine = create_engine(
    URL.create(
        db_config['drivername'],
        db_config['username'],
        db_config['password'],
        db_config['host'],
        db_config['port'],
        db_config['database']
    ),
    connect_args={'charset': 'utf8mb4', 'use_unicode': True},
    pool_pre_ping=True,
    pool_recycle=1800,
)

Base.metadata.create_all(bind=engine, checkfirst=True)

with open("config.json") as jsonfile:
    sentinels = load(jsonfile)['sentinels']

for key in sentinels: 
    Session = sessionmaker(bind=engine)
    session = Session()

    new_sentinel = Sentinel(phone = sentinels[key]['phone'], name = sentinels[key]['name'])

    db_sentinel = session.query(Sentinel).filter_by(phone=sentinels[key]['phone']).first()

    if not db_sentinel:
        session.add(new_sentinel)
    
    session.flush()
    session.commit()
    session.close()

