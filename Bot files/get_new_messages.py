import asyncio
import json
import database
from alchemy import Entity
from telethon import TelegramClient
from datetime import datetime
import logging
from telethon.tl.types import PeerChannel
from telethon.errors import MessageIdInvalidError
from telethon import functions, types
from sqlalchemy.orm import sessionmaker
from update_comments import update_comment_levels_sql

date = datetime.now().strftime('%Y-%m-%d')

logging.basicConfig(
    level=logging.ERROR,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename=f'error_log_{date}.txt',
    filemode='a',
    encoding='utf-8'
)

async def main():
    with open("config.json") as jsonfile:
        sentinels = json.load(jsonfile)['sentinels']

    Session = sessionmaker(bind=database.engine)

    for key in sentinels: 
        try:
            async with TelegramClient(sentinels[key]['name'], sentinels[key]['id'], sentinels[key]['hash']) as client:
                print(f"Client for {sentinels[key]['name']} connected. Checking for new messages...")
                
                session = Session()

                batch_counter = 0 #Batching

                database_dialogs = session.query(Entity).filter_by(
                    type = 'Channel',
                ).all()

                database_dialog_ids = {d.telegram_id for d in database_dialogs}
                
                async for dialog in client.iter_dialogs():

                    try:

                        if str(dialog.entity.id) not in database_dialog_ids:
                            print("[SKIP] Dialog not in database dialogs")
                            continue

                        if dialog.entity is None:
                            logging.warning(f"[SKIP] Found Zombie Dialog (ID: {dialog.id}) with no entity.")
                            continue

                        if (type(dialog.entity).__name__ == 'User'):
                            continue

                        try:
                            with open(f"progress_log_{date}.txt", "a", encoding="utf-8") as f:
                                d_name = getattr(dialog, 'name', 'Unknown')
                                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                                f.write(f"[{timestamp}] Checking chat: {d_name} (ID: {dialog.id})\n")
                        except Exception as log_e:
                            print(f"CRITICAL WARNING: Could not write to progress_log_{date}.txt for chat {dialog.id}. Error: {log_e}")

                        first_id = database.get_first_id(dialog, -30)
                        
                        async for message in client.iter_messages(dialog.entity.id, min_id=first_id[0] if first_id[0] else 0, reverse = True):
                            #Reversed, so older messages first

                            try:

                                database.save_message(session, dialog, message)

                                batch_counter += 1

                                if dialog.entity.broadcast and message.replies and message.replies.replies > 0:
                                    try:
                                        try:
                                            input_peer = await client.get_input_entity(dialog.entity)
                                            #Get discussion group with GetDiscussionMessageRequest
                                            discussion = await client(functions.messages.GetDiscussionMessageRequest(
                                                peer=input_peer,
                                                msg_id=message.id
                                            ))
                                        except Exception as e:
                                            logging.error(f"[WARN] Could not resolve discussion for message {message.id} in '{dialog.name}': {e}")
                                            continue

                                        if not discussion or not discussion.messages:
                                            logging.error(f"[INFO] No discussion mapping for message {message.id} in '{dialog.name}'")
                                            continue

                                        discussion_msg = discussion.messages[0]
                                        discussion_chat_id = None

                                        if discussion.chats and len(discussion.chats) > 0:
                                            discussion_chat_id = discussion.chats[0].id

                                        if not discussion_chat_id:
                                            logging.error(f"[WARN] Could not resolve discussion chat for post {message.id} in '{dialog.name}'")
                                            continue

                                        async for comment in client.iter_messages((discussion_chat_id), reply_to = discussion_msg.id, limit = 1000):
                                            try:
                                                # Check if the reply is replying to id
                                                is_top_level = False
                                                if (comment.reply_to and hasattr(comment.reply_to, "reply_to_msg_id")):
                                                    if comment.reply_to.reply_to_msg_id == discussion_msg.id:
                                                        is_top_level = True
                                                
                                                # Assign Level
                                                temp_level = 1 if is_top_level else -1

                                                database.save_comment(
                                                    session,
                                                    comment_message=comment,
                                                    parent_post_id=message.id,
                                                    parent_channel_id=message.chat_id,
                                                    level=temp_level #Level indicates the "topology" of the comments
                                                )

                                                batch_counter += 1
                                                
                                            except Exception as comment_e:
                                                logging.error(f"Could not resolve comments for message {message.id}. Error: {comment_e}")
                                                continue

                                    except Exception as comment_e:
                                        logging.error(f"Could not fetch comments for message {message.id}. Error: {comment_e}")
                                        continue
                                    
                                if (batch_counter >= 100):
                                    try:
                                        session.commit()
                                        print(f"Committed batch of {batch_counter} items")
                                        batch_counter = 0
                                    except Exception as e:
                                        logging.error(f"Batch commit failed: {e}")
                                        session.rollback() # Only rollback if commit fails
                                        batch_counter = 0
                            
                            except Exception as e:
                                error_details = (f"\n{'='*50}\n[ERROR] Failed to save message\nChat: {dialog.name} (ID: {dialog.id})\n"
                                                f"Message ID: {message.id}\nError Details: {e}\nFull Message JSON: {message.to_json(indent=4)}\n{'='*50}")
                                logging.error(error_details)
                                continue
                    except Exception as dialog_e:
                        logging.error(f"CRITICAL WARNING: Error processing dialog {dialog.id}: {dialog_e}")
                        continue
            #Final commit
            try:
                session.commit()
                print("Pushed final commit")
            except Exception as e:
                logging.error(f"[ERROR] Sentinel {sentinels[key]['name']} final commit failed: {e}")
                session.rollback()
            
            session.close()
        except Exception as client_e:
            logging.critical(f"A critical error occurred with client {sentinels[key]['name']}: {client_e}")

    print("Finished checking messages for all sentinels.")

    print("Updating comment level logic for all sentinels...")

    try:
        update_comment_levels_sql()
        print("Finished updating comments.")
        
    except Exception as e:
        logging.error(f"[ERROR] Comment updating logic failed: {e}")
        print(f"Comment updating logic failed: {e}")
    
    print(f"Program finished at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    asyncio.run(main())

