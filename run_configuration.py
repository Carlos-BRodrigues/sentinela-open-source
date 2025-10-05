from alchemy import Entity, Message, Sentinel, Media
from json import load
from sqlalchemy import create_engine
from sqlalchemy.engine.url import URL
from sqlalchemy.orm import sessionmaker



# Criando tabelas
with open("config.json") as jsonfile:
    db_config = load(jsonfile)['database']

engine = create_engine(URL.create(db_config['drivername'], db_config['username'], db_config['password'], db_config['host'], db_config['port'], db_config['database']))

Sentinel.__table__.create(bind=engine, checkfirst=True)
Entity.__table__.create(bind=engine, checkfirst=True)
Message.__table__.create(bind=engine, checkfirst=True)
Media.__table__.create(bind=engine, checkfirst=True)

with open("config.json") as jsonfile:
    sentinels = load(jsonfile)['sentinels']

for key in sentinels: 
    Session = sessionmaker(bind=engine)
    session = Session()

    new_sentinel = Sentinel(phone = sentinels[key]['phone'], name = sentinels[key]['name'])

    session.add(new_sentinel)
    session.flush()
    session.commit()
    session.close()

