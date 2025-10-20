import asyncio
import json
from telethon import TelegramClient
import database

async def main():
    with open("config.json") as jsonfile:
        sentinels = json.load(jsonfile)['sentinels']

    for key in sentinels:
        async with TelegramClient(sentinels[key]['name'], sentinels[key]['id'], sentinels[key]['hash']) as client:
            
            print(f"Client for {sentinels[key]['name']} is connected. Fetching dialogs...")
            
            async for dialog in client.iter_dialogs():
                if (dialog.entity.id > 0):
                    database.update_entities(dialog, sentinels[key])
            
            print(f"Finished fetching dialogs for {sentinels[key]['name']}.")

if __name__ == "__main__":
    asyncio.run(main())