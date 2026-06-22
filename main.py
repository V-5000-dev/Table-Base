import discord
from discord.ext import commands, tasks
from datetime import datetime
from dotenv import load_dotenv
import logging
import os
import json
import io

import config
from utils import load_settings, save_settings
from enum import Enum

def json_safe(obj):
    if isinstance(obj, dict):
        return {
            (k.name if isinstance(k, Enum) else str(k) if not isinstance(k, (str, int, float, bool, type(None))) else k):
            json_safe(v)
            for k, v in obj.items()
        }
    elif isinstance(obj, list):
        return [json_safe(v) for v in obj]
    elif isinstance(obj, Enum):
        return obj.name  
    else:
        return obj

logging.basicConfig(
    filename="bot.log",
    level=logging.INFO,
    format="%(asctime)s %(message)s"
)

load_dotenv(dotenv_path=".env")


def get_prefix(bot, message):
    if message.guild:
        return config.get_guild(message.guild.id)["COMMAND_PREFIX"]
    return "t! "


class Client(commands.Bot):

    async def setup_hook(self):
        load_settings()  # must run before any cog calls config.get_guild()

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
        await self.load_extension("cogs.dev_control")
        await self.load_extension("cogs.ping_swat")
        await self.load_extension("cogs.dev_restore_settings")
        await self.load_extension("cogs.dev_cat_file")
        await self.load_extension("cogs.prefix")
        await self.load_extension("cogs.set_prefix")

        synced = await self.tree.sync()
        print(f"Synced {len(synced)} commands")

    @tasks.loop(hours=24)
    async def backup_tables(self):
        for guild_id, guild_settings in config.GUILD_SETTINGS.items():
            channel_id = guild_settings.get("TABLE_BACKUP_CHANNEL_ID", 0)
            if not channel_id:
                continue

            channel = self.get_channel(channel_id)
            if channel:
                unix_time = int(datetime.now().timestamp())
                guild_data = json.dumps(
    json_safe({str(guild_id): guild_settings}),
    indent=4
)
                await channel.send(
                    content=f"Settings Backup\n🕒 <t:{unix_time}:F>",
                    file=discord.File(io.BytesIO(guild_data.encode()), filename="settings.json")
            )
    async def on_ready(self):
        save_settings()  # write back any new default keys added since last run

        if not self.backup_tables.is_running():
            self.backup_tables.start()

        print(f"Logged in as {self.user}")


intents = discord.Intents.default()
intents.message_content = True

client = Client(
    command_prefix=get_prefix,
    intents=intents
)

client.run(os.getenv("TOKEN"))