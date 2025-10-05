from telethon.sync import TelegramClient
import json
import database


with open("config.json") as jsonfile:
    sentinels = json.load(jsonfile)['sentinels']

for key in sentinels: 
    with TelegramClient(sentinels[key]['name'], sentinels[key]['id'], sentinels[key]['hash']) as client:
        for dialog in client.iter_dialogs():
            last_id = database.get_last_id(dialog)
            first_id = database.get_first_id(dialog, -7)
            print(dialog.entity.id)
            
            if (type(dialog.entity).__name__ != 'User'):
                for message in client.iter_messages(dialog.entity.id, min_id=first_id[0] if first_id[0] else 0 ):
                    # print(message.reply_to.reply_to_msg_id if message.reply_to else None)
                    database.save_message(dialog, message)
