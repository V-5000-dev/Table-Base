import discord
from discord.ext import commands
from discord import app_commands
from config import GUILD_ID, CHECK, CHECKWHITE, CommandType
from utils import verifyCommandPermissions

class Prefix(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="prefix", description="Check the commannd prefix.")
    async def ping(self, interaction: discord.Interaction):
        if not await verifyCommandPermissions(interaction):
            return
        await interaction.response.send_message(f"``The command prefix is set to:`` ``{self.bot.command_prefix}``\n``Server Admins can change this with`` ``set-prefix.``")
    @commands.command(name="prefix")
    async def ping_prefix(self, ctx):
        if not await verifyCommandPermissions(ctx):
            return
        await ctx.send(f"``The command prefix is set to:`` ``{self.bot.command_prefix}``\n``Server Admins can change this with`` ``set-prefix.``")

async def setup(bot):
    await bot.add_cog(Prefix(bot))