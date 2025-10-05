import json
import datetime


from sqlalchemy import create_engine, func
from sqlalchemy.engine.url import URL
from sqlalchemy.orm import sessionmaker

from alchemy import Entity, Message, Sentinel, Media


with open("config.json") as jsonfile:
    db_config = json.load(jsonfile)['database']


engine = create_engine(URL.create(db_config['drivername'], db_config['username'], db_config['password'], db_config['host'],
                                  db_config['port'], db_config['database']))


def update_entities(dialog, sentinel):
    Session = sessionmaker(bind=engine)
    session = Session()

    old_entity = session.query(Entity).filter_by(
        telegram_id=str(dialog.entity.id)).filter_by(type=type(dialog.entity).__name__).first()

    db_sentinel = session.query(Sentinel).filter_by(
        phone=sentinel['phone']).first()

    if (old_entity):
        old_entity.verified = dialog.entity.verified if hasattr(
            dialog.entity, 'verified') else False
        old_entity.participants_count = dialog.entity.participants_count if hasattr(
            dialog.entity, 'participants_count') else 0

    else:
        new_entity = Entity(type=type(dialog.entity).__name__,
                            telegram_id=str(dialog.entity.id),
                            participants_count=dialog.entity.participants_count if hasattr(
                                dialog.entity, 'participants_count') else 0,
                            collected_by=db_sentinel.id,
                            username=dialog.entity.username if hasattr(
            dialog.entity, 'username') else '-',
            verified=dialog.entity.verified if hasattr(
                dialog.entity, 'verified') else False,
            broadcast=dialog.entity.broadcast if hasattr(
                dialog.entity, 'broadcast') else False,
            megagroup=dialog.entity.megagroup if hasattr(
                dialog.entity, 'megagroup') else False,
            gigagroup=dialog.entity.gigagroup if hasattr(
                dialog.entity, 'gigagroup') else False,
            name=dialog.entity.title if (type(dialog.entity).__name__ != 'User') else
            (dialog.entity.first_name if hasattr(dialog.entity, 'first_name') else "-" +
             " " + dialog.entity.last_name if hasattr(dialog.entity, 'last_name') else '-')
        )

        session.add(new_entity)
        session.flush()

    session.commit()
    session.close()


def get_entities():
    Session = sessionmaker(bind=engine)
    session = Session()

    return session.query(Entity).all()


def get_last_id(dialog):
    Session = sessionmaker(bind=engine)
    session = Session()

    db_entity = session.query(Entity).filter_by(
        telegram_id=str(dialog.entity.id)).first()
    result = session.query(func.max(Message.message_id)).filter_by(
        entity_id=db_entity.id).first()

    session.close()

    return result


def get_first_id(dialog, days_qty):
    Session = sessionmaker(bind=engine)
    session = Session()

    db_entity = session.query(Entity).filter_by(telegram_id=dialog.entity.id).first()
    result = session.query(func.min(Message.message_id)).filter_by(entity_id=db_entity.id).filter(
        Message.date > datetime.date.today() + datetime.timedelta(days=days_qty)).first()

    session.close()

    return result


def save_message(dialog, t_message):
    Session = sessionmaker(bind=engine)
    session = Session()

    db_entity = session.query(Entity).filter_by(telegram_id=str(dialog.entity.id)).first()

    old_message = session.query(Message).filter_by(entity_id=db_entity.id).filter(Message.message_id == t_message.id).first()
    
    if (old_message):
        old_message.forwards = t_message.forwards
        old_message.reply_to_id = t_message.reply_to.reply_to_msg_id if t_message.reply_to else None,
        old_message.views = t_message.views
        old_message.message = t_message.message
        old_message.edit_date = t_message.editdate if hasattr(t_message, 'editdate') else None
        old_message.fwd_from_id_message = t_message.fwd_from.channel_post if t_message.fwd_from is not None and t_message.fwd_from.channel_post is not None else None
        old_message.fwd_from_id = list(vars(t_message.fwd_from.from_id).values())[0] if t_message.fwd_from is not None and t_message.fwd_from.from_id is not None else None
    else: 
        new_message = Message(
            message_id=t_message.id,
            message=t_message.message,
            entity_id=db_entity.id,
            date=t_message.date,
            edit_date=t_message.editdate if hasattr(
                t_message, 'editdate') else None,
            author=t_message.from_id.user_id if hasattr(t_message, 'from_id') and hasattr(t_message.from_id, 'user_id') else t_message.from_id.channel_id if hasattr(
                    t_message, 'from_id') and hasattr(t_message.from_id, 'channel_id') else None,
            forwards=t_message.forwards,
            views=t_message.views,
            reply_to_id = t_message.reply_to.reply_to_msg_id if t_message.reply_to else None,
            fwd_from_id_message = t_message.fwd_from.channel_post if t_message.fwd_from is not None and t_message.fwd_from.channel_post is not None else None,
            fwd_from_id = list(vars(t_message.fwd_from.from_id).values())[0] if t_message.fwd_from is not None and t_message.fwd_from.from_id is not None else None,
            fwd_from_type = type(t_message.fwd_from.from_id).__name__ if t_message.fwd_from is not None and t_message.fwd_from.from_id is not None else None,
        )

        session.add(new_message)
        session.flush()

        if hasattr(t_message.media, 'document'):
            new_media = Media(
                message_id = new_message.id,
                media_id = t_message.media.document.id,
                access_hash = t_message.media.document.access_hash,
                file_reference = t_message.media.document.file_reference,
                date = t_message.media.document.date,
                mime_type = t_message.media.document.mime_type
            )

            session.add(new_media)

    session.commit()
    session.close()


def date_format(message):
    if type(message) is datetime:
        return message.strftime("%Y-%m-%d %H:%M:%S")
