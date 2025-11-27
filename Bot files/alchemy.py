from sqlalchemy import *
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.mysql import LONGTEXT
from sqlalchemy import BigInteger

Base = declarative_base()

class Entity(Base):
    __tablename__ = 'telegram_entities'

    id = Column(Integer, primary_key=True)
    collected_by = Column(Integer, ForeignKey("telegram_sentinels.id"), nullable=False)
    type = Column(Text)
    telegram_id = Column(Text)
    name = Column(LONGTEXT)
    participants_count = Column(Integer)
    username = Column(LONGTEXT)
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
    message = Column(LONGTEXT)
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
    message_id = Column(Integer, ForeignKey("telegram_messages.id"), nullable=True)
    comment_id = Column(Integer, ForeignKey("telegram_comments.id"), nullable=True)
    media_id = Column(Text)
    access_hash = Column(Text)
    file_reference = Column(Text)
    date = Column(DateTime)
    mime_type = Column(Text)
    backup_link = Column(Text)

    def __repr__(self):
        return f'Media {self.file_reference}'

class Reaction(Base):
    __tablename__ = 'telegram_reactions'

    id = Column(Integer, primary_key=True)
    message_id = Column(Integer, ForeignKey("telegram_messages.id"), nullable=True, index=True)
    comment_id = Column(Integer, ForeignKey("telegram_comments.id"), nullable=True, index=True)
    reaction = Column(Text)
    count = Column(Integer)

    UniqueConstraint('message_id', 'reaction', name='unique_reaction_for_message')

    def __repr__(self):
        return f'Reaction {self.reaction} ({self.count})'

class Comment(Base):
    __tablename__ = 'telegram_comments'

    id = Column(Integer, primary_key=True)
    comment_id = Column(Integer, index=True)
    discussion_group_id = Column(BigInteger)
    comment_text = Column(LONGTEXT)
    author_id = Column(Integer)
    date = Column(DateTime)
    edit_date = Column(DateTime)
    
    parent_post_message_id = Column(Integer, ForeignKey("telegram_messages.id"), index=True)
    parent_post_entity_id = Column(Integer, ForeignKey("telegram_entities.id"), nullable=False)

    reply_to_comment_id = Column(Integer)

    UniqueConstraint('parent_post_message_id', 'comment_id', name='unique_comment')
    
    def __repr__(self):
        return f'Comment {self.comment_id}'