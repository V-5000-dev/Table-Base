import discord
from discord.ext import commands
from dotenv import load_dotenv
import logging
import os
from config import GUILD_ID
from utils import load_settings

logging.basicConfig(filename="bot.log", level=logging.INFO, format="%(asctime)s %(message)s")
load_dotenv(dotenv_path=".env")

class Client(commands.Bot):
    async def setup_hook(self):
        await self.load_extension("cogs.ping")
        await self.load_extension("cogs.database_create")
        await self.load_extension("cogs.server_settings")
        await self.load_extension("cogs.prefix")
        await self.load_extension("cogs.table")
        self.tree.copy_global_to(guild=GUILD_ID)
        synced = await self.tree.sync(guild=GUILD_ID)
        print(f"Synced {len(synced)} commands: {[c.name for c in synced]}")

    async def on_ready(self):
        load_settings()
        print(f"Logged in as {self.user}.")

intents = discord.Intents.default()
intents.message_content = True
client = Client(command_prefix="db ", intents=intents)
client.run(os.getenv('TOKEN'))