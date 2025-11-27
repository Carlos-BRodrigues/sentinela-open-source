import json
import datetime
from sqlalchemy import create_engine, func
from sqlalchemy.engine.url import URL
from sqlalchemy.orm import sessionmaker
import logging
from telethon.tl.types import ReactionEmoji, ReactionPaid

from alchemy import Entity, Message, Sentinel, Media, Reaction, Comment


logging.basicConfig(
    level=logging.ERROR,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='error_log.txt',
    filemode='a',
    encoding='utf-8'
)


with open("config.json") as jsonfile:
    db_config = json.load(jsonfile)['database']


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

def normalize_channel_id_for_entity_lookup(v):
    # Accepts ints or strings. Removes -100 prefix if present for legacy negative IDs.
    if v is None:
        return None
    s = str(v)
    if s.startswith('-100'):
        return s[4:]
    if s.startswith('-'):
        return s.lstrip('-')
    return s

def sanitize_for_db(s):
    """
    Return a UTF-8-safe string suitable for insertion into a utf8mb4 MySQL column.
      - If input is bytes, try utf-8 decode else base64 (not used here).
      - If input is str, encode with 'surrogatepass' to keep well-formed Unicode bytes,
        then decode with 'replace' so any illegal bytes become U+FFFD rather than raising.
    This removes lone surrogate errors while preserving real emojis.
    """
    if s is None:
        return None
    if isinstance(s, bytes):
        try:
            return s.decode('utf-8')
        except Exception:
            import base64
            return base64.b64encode(s).decode('ascii')
    if isinstance(s, str):
        # encode with surrogatepass (allows encoding lone surrogates), then decode with replace
        try:
            return s.encode('utf-8', 'surrogatepass').decode('utf-8', 'replace')
        except Exception:
            # fallback: drop bad parts
            return s.encode('utf-8', 'ignore').decode('utf-8', 'ignore')
    return str(s)


def update_entities(dialog, sentinel):
    Session = sessionmaker(bind=engine)
    session = Session()

    old_entity = session.query(Entity).filter_by(
        telegram_id=str(dialog.entity.id)).filter_by(type=type(dialog.entity).__name__).first()

    db_sentinel = session.query(Sentinel).filter_by(
        phone=sentinel['phone']).first()

    if old_entity:
        old_entity.verified = getattr(dialog.entity, 'verified', False)
        old_entity.participants_count = getattr(dialog.entity, 'participants_count', 0)
    else:
        first_name = sanitize_for_db(getattr(dialog.entity, 'first_name', ''))
        last_name = sanitize_for_db(getattr(dialog.entity, 'last_name', ''))
        name = f"{first_name} {last_name}".strip()
        
        new_entity = Entity(
            type=type(dialog.entity).__name__,
            telegram_id=str(dialog.entity.id),
            participants_count=getattr(dialog.entity, 'participants_count', 0),
            collected_by=db_sentinel.id,
            username=sanitize_for_db(getattr(dialog.entity, 'username', '-')),
            verified=getattr(dialog.entity, 'verified', False),
            broadcast=getattr(dialog.entity, 'broadcast', False),
            megagroup=getattr(dialog.entity, 'megagroup', False),
            gigagroup=getattr(dialog.entity, 'gigagroup', False),
            name=sanitize_for_db(getattr(dialog.entity, 'title', name)) # Use title if it exists, otherwise use constructed name
        )

        try:
            session.add(new_entity)
        except Exception as e:
            session.rollback()
            logging.error("DB entity insert failed")

    try:
        session.commit()
    except Exception as e:
        session.rollback()
        logging.error(f"Commit failed: {e}")
    finally:
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
    
    if not db_entity:
        session.close()
        return
    db_message = session.query(Message).filter_by(entity_id=db_entity.id, message_id=t_message.id).first()
    
    author_id = None
    if t_message.from_id:
        if hasattr(t_message.from_id, 'user_id'):
            author_id = t_message.from_id.user_id
        elif hasattr(t_message.from_id, 'channel_id'):
            author_id = t_message.from_id.channel_id

    fwd_from_id = None
    fwd_from_type = None
    fwd_from_id_message = None
    if t_message.fwd_from:
        fwd_from_id_message = getattr(t_message.fwd_from, 'channel_post', None)
        from_id_peer = getattr(t_message.fwd_from, 'from_id', None)
        if from_id_peer:
            fwd_from_type = from_id_peer.__class__.__name__
            if hasattr(from_id_peer, 'user_id'):
                fwd_from_id = from_id_peer.user_id
            elif hasattr(from_id_peer, 'channel_id'):
                fwd_from_id = from_id_peer.channel_id

    if db_message:
        db_message.message = sanitize_for_db(t_message.message)
        db_message.forwards = t_message.forwards
        db_message.views = t_message.views
        db_message.edit_date = t_message.edit_date
    else: 
        db_message = Message(
            message_id=t_message.id,
            message=sanitize_for_db(t_message.message),
            entity_id=db_entity.id,
            date=t_message.date,
            edit_date=t_message.edit_date,
            author=author_id,
            forwards=t_message.forwards,
            views=t_message.views,
            reply_to_id=getattr(t_message.reply_to, 'reply_to_msg_id', None),
            fwd_from_id_message=fwd_from_id_message,
            fwd_from_id=fwd_from_id,
            fwd_from_type=fwd_from_type
        )
        try:
            session.add(db_message)
            session.flush()
        except Exception as e:
            session.rollback()
            logging.error("DB message insert failed")

    if t_message.reactions:
        for reaction_count in t_message.reactions.results:
            
            reaction_text = ''
            if isinstance(reaction_count.reaction, ReactionEmoji):
                reaction_text = sanitize_for_db(reaction_count.reaction.emoticon)
            elif isinstance(reaction_count.reaction, ReactionPaid):
                reaction_text = '[PAID]'
            else:
                reaction_text = '[CUSTOM / OTHER]'

            db_reaction = session.query(Reaction).filter_by(
                message_id=db_message.id, 
                reaction=reaction_text
            ).first()

            if db_reaction:
                db_reaction.count = reaction_count.count
            else:
                new_reaction = Reaction(
                    message_id=db_message.id,
                    reaction=sanitize_for_db(reaction_text),
                    count=reaction_count.count
                )
                try:
                    session.add(new_reaction)
                except Exception as e:
                    session.rollback()
                    logging.error("DB reaction insert failed")

    if t_message.media and hasattr(t_message.media, 'document'):
        doc = t_message.media.document
        media_id_str = str(doc.id)

        try:
            existing_media = session.query(Media).filter_by(media_id=media_id_str).first()
        except Exception as e:
            session.rollback()
            logging.error(f"DB query failed when looking for media {media_id_str}: {e}")
            existing_media = None

        if not existing_media:
            new_media = Media(
                message_id=db_message.id,
                media_id=media_id_str,
                access_hash=sanitize_for_db(getattr(doc, 'access_hash', None)),
                file_reference=sanitize_for_db(getattr(doc, 'file_reference', None)),
                date=getattr(doc, 'date', None),
                mime_type=sanitize_for_db(getattr(doc, 'mime_type', None))
            )
            try:
                session.add(new_media)
                session.flush()
            except Exception as e:
                session.rollback()
                logging.error(f"DB media insert failed: {e}")
    try:
        session.commit()
    except Exception as e:
        session.rollback()
        logging.error(f"Commit failed: {e}")
    finally:
        session.close()


def save_comment(comment_message, parent_post_id, parent_channel_id):
    Session = sessionmaker(bind=engine)
    session = Session()

    normalized_id = normalize_channel_id_for_entity_lookup(parent_channel_id)

    if normalized_id is None:
        logging.error(f"[SKIP] parent_channel_id is None for comment {comment_message.id}")
        return

    db_parent_entity = session.query(Entity).filter_by(telegram_id=normalized_id).first()
    
    parent_db_message = session.query(Message).filter_by(
            entity_id=db_parent_entity.id,
            message_id=int(parent_post_id)
        ).first()

    if not db_parent_entity:
        logging.error(f"[SKIP] No parent entity found for comment {comment_message.id} in channel {parent_channel_id}")
        session.close()
        return

    if not parent_db_message:
            logging.error(f"[SKIP] Parent DB message not found for telegram message_id={parent_post_id} in entity {db_parent_entity.id}.")
            session.close()
            return
    else:
        parent_db_message_id = parent_db_message.id

    try:
        exists = session.query(Comment).filter_by(
            comment_id=int(getattr(comment_message, 'id', None)),
            parent_post_message_id=parent_db_message_id
        ).first()

    except:
        logging.error("[SKIP] Error in comment query, probably because of comment_id")
        session.close()
        return

    if exists:
            exists.comment_text = sanitize_for_db(getattr(comment_message, 'text', None))
            exists.edit_date = getattr(comment_message, 'edit_date', None)
            exists.discussion_group_id=comment_message.chat_id

            if parent_db_message_id and exists.parent_post_message_id != parent_db_message_id:
                exists.parent_post_message_id = parent_db_message_id
                exists.parent_post_entity_id = db_parent_entity.id
            
            try:
                session.commit()
            except Exception as e:
                session.rollback()
                logging.error(f"DB comment update failed for {comment_message.id}: {e}")
            session.close()
            return

    if not exists:
        try:
            new_comment = Comment(
                comment_id=comment_message.id,
                discussion_group_id=comment_message.chat_id,
                comment_text=sanitize_for_db(getattr(comment_message, 'text', None)),
                author_id=getattr(getattr(comment_message, 'from_id', None), 'user_id', None),
                date=getattr(comment_message, 'date', None),
                edit_date = getattr(comment_message, 'edit_date', None),
                parent_post_message_id=parent_db_message_id,
                parent_post_entity_id=db_parent_entity.id,
                reply_to_comment_id=getattr(getattr(comment_message, 'reply_to', None), 'reply_to_msg_id', None)
            )
            try:
                session.add(new_comment)
                session.flush()
            except Exception as e:
                    session.rollback()
                    logging.error("DB comment insert failed")

            if getattr(comment_message, 'media', None) and hasattr(comment_message.media, 'document'):
                doc = comment_message.media.document
                media_id_str = str(doc.id)
                try:
                    existing_media = session.query(Media).filter_by(media_id=media_id_str).first()
                except Exception as e:
                    session.rollback()
                    logging.error(f"DB query failed when looking for media {media_id_str}: {e}")
                    existing_media = None

                if not existing_media:
                    new_media = Media(
                        comment_id=new_comment.id,  # link to comment (if your schema allows) OR leave as message_id
                        media_id=media_id_str,
                        access_hash=sanitize_for_db(getattr(doc, 'access_hash', None)),
                        file_reference=sanitize_for_db(getattr(doc, 'file_reference', None)),
                        date=getattr(doc, 'date', None),
                        mime_type=sanitize_for_db(getattr(doc, 'mime_type', None))
                    )
                    try:
                        session.add(new_media)
                    except Exception as e:
                        session.rollback()
                        logging.error("DB media comment insert failed")

            if getattr(comment_message, 'reactions', None) and hasattr(comment_message.reactions, 'results'):
                for reaction_count in comment_message.reactions.results:
                    reaction_text = ''
                    if isinstance(reaction_count.reaction, ReactionEmoji):
                        reaction_text = sanitize_for_db(reaction_count.reaction.emoticon)
                    elif isinstance(reaction_count.reaction, ReactionPaid):
                        reaction_text = '[PAID]'
                    else:
                        reaction_text = '[CUSTOM / OTHER]'

                    db_reaction = session.query(Reaction).filter_by(
                        comment_id=new_comment.id,
                        reaction=reaction_text
                    ).first()

                    if db_reaction:
                        db_reaction.count = reaction_count.count
                    else:
                        new_reaction = Reaction(
                            comment_id=new_comment.id,
                            reaction=sanitize_for_db(reaction_text),
                            count=reaction_count.count
                        )
                        try:
                            session.add(new_reaction)
                        except Exception as e:
                            session.rollback()
                            logging.error("DB comment reaction insert failed")

            session.commit()
        except Exception as e:
            session.rollback()
            logging.error(f"DB comment insert failed for {comment_message.id}: {e}")
    session.close()

def date_format(message):
    if type(message) is datetime:
        return message.strftime("%Y-%m-%d %H:%M:%S")
