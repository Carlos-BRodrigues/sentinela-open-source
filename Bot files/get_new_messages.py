import asyncio
import json
import database
from telethon import TelegramClient
from datetime import datetime
import logging
from telethon.tl.types import PeerChannel
from telethon.errors import MessageIdInvalidError
from telethon import functions, types

logging.basicConfig(
    level=logging.ERROR,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='error_log.txt',
    filemode='a',
    encoding='utf-8'
)

async def main():
    with open("config.json") as jsonfile:
        sentinels = json.load(jsonfile)['sentinels']

    date = datetime.now().strftime('%Y-%m-%d')

    for key in sentinels: 
        try:
            async with TelegramClient(sentinels[key]['name'], sentinels[key]['id'], sentinels[key]['hash']) as client:
                print(f"Client for {sentinels[key]['name']} connected. Checking for new messages...")
                
                async for dialog in client.iter_dialogs():
                    
                    try:
                        with open(f"progress_log_{date}.txt", "a", encoding="utf-8") as f:
                            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                            f.write(f"[{timestamp}] Checking chat: {dialog.name} (ID: {dialog.id})\n")
                    except Exception as log_e:
                        print(f"CRITICAL WARNING: Could not write to progress_log_{date}.txt for chat {dialog.name}. Error: {log_e}")

                    if (type(dialog.entity).__name__ == 'User'):
                        continue

                    first_id = database.get_first_id(dialog, -7)
                    
                    async for message in client.iter_messages(dialog.entity.id, min_id=first_id[0] if first_id[0] else 0):
                        try:
                            database.save_message(dialog, message)

                            if dialog.entity.broadcast and message.replies and message.replies.replies > 0:
                                try:
                                    try:
                                        input_peer = await client.get_input_entity(dialog.entity)
                                        discussion = await client(functions.messages.GetDiscussionMessageRequest(
                                            peer=input_peer,
                                            msg_id=message.id
                                        ))
                                    except Exception as e:
                                        logging.error(f"Could not resolve discussion for message {message.id} in '{dialog.name}': {e}")
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

                                    async for comment in client.iter_messages(discussion_chat_id, reply_to = discussion_msg.id, limit = 1000):

                                        # Gets only top-level replies
                                        if (
                                            comment.reply_to and hasattr(comment.reply_to, "reply_to_msg_id") and comment.reply_to.reply_to_msg_id == discussion_msg.id
                                        ):  
                                            
                                            database.save_comment(
                                                comment_message=comment,
                                                parent_post_id=message.id,
                                                parent_channel_id=message.chat_id
                                            )
                                            
                                        else:
                                            # Skip unrelated replies or stray messages
                                            continue

                                except Exception as comment_e:
                                    logging.error(f"Could not fetch comments for message {message.id}. Error: {comment_e}")
                                    continue
                        
                        except Exception as e:
                            error_details = (f"\n{'='*50}\nFailed to save message\nChat: {dialog.name} (ID: {dialog.id})\n"
                                             f"Message ID: {message.id}\nError Details: {e}\nFull Message JSON: {message.to_json(indent=4)}\n{'='*50}")
                            logging.error(error_details)
                            continue
        
        except Exception as client_e:
            logging.error(f"A critical error occurred with client {sentinels[key]['name']}: {client_e}")
            logging.critical(f"A critical error occurred with client {sentinels[key]['name']}: {client_e}")

    print("Finished checking messages for all sentinels.")

if __name__ == "__main__":
    asyncio.run(main())

