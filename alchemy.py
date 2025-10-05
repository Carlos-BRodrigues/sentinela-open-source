from sqlalchemy import *
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class Entity(Base):
    __tablename__ = 'telegram_entities'

    id = Column(Integer, primary_key=True)
    collected_by = Column(Integer, ForeignKey("telegram_sentinels.id"), nullable=False)
    type = Column(Text)
    telegram_id = Column(Text)
    name = Column(Text)
    participants_count = Column(Integer)
    username = Column(Text)
    broadcast = Column(Boolean)
    verified = Column(Boolean)
    megagroup = Column(Boolean)
    gigagroup = Column(Boolean)

    UniqueConstraint('collected_by', 'telegram_id', name='unique_entity')


    def __repr__(self):
        return f'Entity {self.name}'


class Message(Base):
    __tablename__ = 'telegram_messages'

    id = Column(Integer, primary_key=True)
    message_id = Column(Integer, index=True)
    message = Column(Text)
    entity_id = Column(Integer, ForeignKey("telegram_entities.id"), nullable=False)
    date = Column(DateTime)
    edit_date = Column(DateTime)
    forwards = Column(Integer)
    views = Column(Integer)
    reply_to_id = Column(Integer)
    author = Column(Integer)
    fwd_from_type = Column(Text)
    fwd_from_id = Column(Integer)
    fwd_from_id_message = Column(Integer)

    UniqueConstraint('entity_id', 'message_id', name='unique_message')

    def __repr__(self):
        return f'Message {self.message}'

class Sentinel(Base):
    __tablename__ = 'telegram_sentinels'

    id = Column(Integer, primary_key=True)
    phone = Column(Text)
    name = Column(Text)

    UniqueConstraint('phone', name='unique_sentinel')

    def __repr__(self):
        return f'Sentinel {self.phone}'

class Media(Base):
    __tablename__ = 'telegram_medias'

    id = Column(Integer, primary_key=True)
    message_id = Column(Integer, ForeignKey("telegram_messages.id"), nullable=False)
    media_id = Column(Text)
    access_hash = Column(Text)
    file_reference = Column(Text)
    date = Column(DateTime)
    mime_type = Column(Text)
    backup_link = Column(Text)

    def __repr__(self):
        return f'Media {self.file_reference}'
