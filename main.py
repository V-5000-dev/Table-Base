import discord
from discord.ext import commands, tasks
from datetime import datetime
from dotenv import load_dotenv
import logging
import os

import config
from utils import load_settings

logging.basicConfig(
    filename="bot.log",
    level=logging.INFO,
    format="%(asctime)s %(message)s"
)

load_dotenv(dotenv_path=".env")


class Client(commands.Bot):

    async def setup_hook(self):
        await self.load_extension("cogs.ping")
        await self.load_extension("cogs.table_create")
        await self.load_extension("cogs.table_delete")
        await self.load_extension("cogs.table_settings")
        await self.load_extension("cogs.table_view_all")
        await self.load_extension("cogs.table_view_user")
        await self.load_extension("cogs.table_view")
        await self.load_extension("cogs.table_add_row_user")
        await self.load_extension("cogs.table_add_row_request")
        await self.load_extension("cogs.table_remove_row_user")
        await self.load_extension("cogs.server_settings")
        await self.load_extension("cogs.dev_key")
        await self.load_extension("cogs.dev_say")
        await self.load_extension("cogs.prefix")
        await self.load_extension("cogs.set_prefix")

        synced = await self.tree.sync()
        print(f"Synced {len(synced)} commands")

    @tasks.loop(hours=24)
    async def backup_settings(self):
        channel = self.get_channel(config.TABLE_BACKUP_CHANNEL_ID)

        if channel and os.path.exists("settings.json"):
            unix_time = int(datetime.now().timestamp())

            await channel.send(
                content=f"Settings Backup\n🕒 <t:{unix_time}:F>",
                file=discord.File("settings.json")
            )

    async def on_ready(self):
        load_settings()

        if not self.backup_settings.is_running():
            self.backup_settings.start()

        print(f"Logged in as {self.user}")


intents = discord.Intents.default()
intents.message_content = True

client = Client(
    command_prefix=config.COMMAND_PREFIX,
    intents=intents
)

client.run(os.getenv("TOKEN"))