import discord
from discord.ext import commands, tasks
from datetime import datetime
from dotenv import load_dotenv
from logging.handlers import RotatingFileHandler
import logging
import os
import json
import io

import config
from config import DEFAULT_PREFIX, ERROR
from utils import load_settings, save_settings, serialize_guild

logging.basicConfig(
    handlers=[RotatingFileHandler("bot.log", maxBytes=5_000_000, backupCount=3, encoding="utf-8")],
    level=logging.INFO,
    format="%(asctime)s %(message)s"
)

load_dotenv(dotenv_path=".env")


def get_prefix(bot, message):
    if message.guild:
        return config.get_guild(message.guild.id)["COMMAND_PREFIX"]
    return DEFAULT_PREFIX


class Client(commands.Bot):

    async def setup_hook(self):
        load_settings()  # must run before any cog calls config.get_guild()

        await self.load_extension("cogs.ping")
        await self.load_extension("cogs.create_table")
        await self.load_extension("cogs.delete_table")
        await self.load_extension("cogs.table_settings")
        await self.load_extension("cogs.view_table")
        await self.load_extension("cogs.view_row_by_user")
        await self.load_extension("cogs.view_row")
        await self.load_extension("cogs.view_row_by_value")
        await self.load_extension("cogs.view_row_by_id")
        await self.load_extension("cogs.add_row_by_user")
        await self.load_extension("cogs.add_row_by_request")
        await self.load_extension("cogs.remove_row_by_id")
        await self.load_extension("cogs.remove_row_by_user")
        await self.load_extension("cogs.server_settings")
        await self.load_extension("cogs.dev_control")
        await self.load_extension("cogs.prefix")
        await self.load_extension("cogs.set_prefix")

        synced = await self.tree.sync()
        print(f"Synced {len(synced)} commands")

    @tasks.loop(hours=24)
    async def backup_tables(self):
        for guild_id, guild_settings in list(config.GUILD_SETTINGS.items()):
            channel_id = guild_settings.get("TABLE_BACKUP_CHANNEL_ID", 0)
            if not channel_id:
                continue

            channel = self.get_channel(channel_id)
            if channel is None:
                continue

            unix_time = int(datetime.now().timestamp())
            guild_data = json.dumps({str(guild_id): serialize_guild(guild_settings)}, indent=4)

            # One server's failure must not stop the backups of the others.
            try:
                await channel.send(
                    content=f"Settings Backup\n🕒 <t:{unix_time}:F>",
                    file=discord.File(io.BytesIO(guild_data.encode()), filename="settings.json")
                )
            except discord.HTTPException:
                logging.exception(f"Could not post the backup for guild {guild_id}")

    async def on_command_error(self, ctx, error):
        if isinstance(error, (commands.CommandNotFound, commands.CheckFailure)):
            return

        if isinstance(error, commands.UserInputError):
            await ctx.send(
                f"{ERROR} ``{error}``\n"
                f"``Usage:`` ``{ctx.clean_prefix}{ctx.command.qualified_name} {ctx.command.signature}``",
                allowed_mentions=discord.AllowedMentions.none()
            )
            return

        logging.error(f"Error in command {ctx.command}", exc_info=error)
        await ctx.send(f"{ERROR} ``Something went wrong running that command.``")

    async def on_ready(self):
        save_settings() 

        if not self.backup_tables.is_running():
            self.backup_tables.start()

        print(f"Logged in as {self.user}")


intents = discord.Intents.default()
intents.message_content = True

client = Client(
    command_prefix=get_prefix,
    intents=intents
)


@client.tree.error
async def on_app_command_error(interaction: discord.Interaction, error):
    logging.error(f"Error in slash command {interaction.command}", exc_info=error)

    message = f"{ERROR} ``Something went wrong running that command.``"
    try:
        if interaction.response.is_done():
            await interaction.followup.send(message, ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)
    except discord.HTTPException:
        pass


client.run(os.getenv("TOKEN"))