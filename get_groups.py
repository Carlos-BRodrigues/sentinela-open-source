from telethon import TelegramClient
import json
import database

api = None
with open("config.json") as jsonfile:
    sentinels = json.load(jsonfile)['sentinels']

for key in sentinels: 
	with TelegramClient(sentinels[key]['name'], sentinels[key]['id'], sentinels[key]['hash']) as client:
		for dialog in client.iter_dialogs():
			if (dialog.entity.id > 0 ):
				database.update_entities(dialog, sentinels[key])