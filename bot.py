import logging
import logging.config
from typing import Optional, Union, AsyncGenerator
from aiohttp import web

# Get logging configurations
logging.config.fileConfig("logging.conf")
logging.getLogger().setLevel(logging.INFO)
logging.getLogger("pyrogram").setLevel(logging.ERROR)
logging.getLogger("imdbpy").setLevel(logging.ERROR)

from pyrogram import Client, __version__, types
from pyrogram.raw.all import layer
from database.ia_filterdb import Media
from database.users_chats_db import db
from info import SESSION, API_ID, API_HASH, BOT_TOKEN, LOG_STR
from utils import temp, scheduler

# Web Server for Koyeb Health Check
async def handle(request):
    return web.Response(text="Bot is Running Live!")

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8080)
    await site.start()
    logging.info("Web Server started on port 8080 for Health Check.")

class Bot(Client):
    def __init__(self):
        super().__init__(
            name=SESSION,
            api_id=API_ID,
            api_hash=API_HASH,
            bot_token=BOT_TOKEN,
            workers=500,
            plugins={"root": "plugins"},
            sleep_threshold=5,
        )

    async def start(self):
        b_users, b_chats = await db.get_banned()
        temp.BANNED_USERS = b_users
        temp.BANNED_CHATS = b_chats
        await super().start()
        
        # വെബ് സർവർ ഇവിടെ സ്റ്റാർട്ട് ചെയ്യുന്നു
        await start_web_server()
        
        scheduler.start()
        await Media.ensure_indexes()
        self.me = await self.get_me()
        temp.ME = self.me.id
        temp.U_NAME = self.me.username
        temp.B_NAME = self.me.first_name
        self.username = "@" + self.me.username
        logging.info(
            f"{self.me.first_name} with for Pyrogram v{__version__} (Layer {layer}) started on {self.me.username}."
        )
        logging.info(LOG_STR)

    async def stop(self, *args):
        await super().stop()
        logging.info("Bot stopped. Bye.")

    async def iter_messages(
        self,
        chat_id: Union[int, str],
        limit: int,
        offset: int = 0,
    ) -> Optional[AsyncGenerator["types.Message", None]]:
        current = offset
        while True:
            new_diff = min(200, limit - current)
            if new_diff <= 0:
                return
            messages = await self.get_messages(
                chat_id, list(range(current, current + new_diff + 1))
            )
            for message in messages:
                yield message
                current += 1

app = Bot()
app.run()
