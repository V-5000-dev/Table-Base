import discord
from discord.ext import commands
from discord import app_commands
from config import GUILD_ID, CHECK, CommandType
from utils import verifyCommandPermissions
import config

class Prefix(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="prefix", description="Checks the command prefix.")
    async def ping(self, interaction: discord.Interaction):
        if not await verifyCommandPermissions(interaction):
            return

        guild_settings = config.get_guild(interaction.guild_id)
        prefix = guild_settings["COMMAND_PREFIX"]
        await interaction.response.send_message(
            f"``The command prefix is set to:`` ``{prefix}``\n``Server Admins can change this with`` ``set-prefix.``"
        )

    @commands.command(name="prefix")
    async def ping_prefix(self, ctx):
        if not await verifyCommandPermissions(ctx):
            return

        guild_settings = config.get_guild(ctx.guild.id)
        prefix = guild_settings["COMMAND_PREFIX"]
        await ctx.send(
            f"``The command prefix is set to:`` ``{prefix}``\n``Server Admins can change this with`` ``set-prefix.``"
        )

async def setup(bot):
    await bot.add_cog(Prefix(bot))