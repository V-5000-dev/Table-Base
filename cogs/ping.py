import discord
from discord.ext import commands
from discord import app_commands
from config import GUILD_ID, CHECK, CHECKWHITE, CommandType
from utils import verifyCommandPermissions

class General(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="ping", description="Checks if the application is online.")
    async def ping(self, interaction: discord.Interaction):
        if not await verifyCommandPermissions(interaction):
            return
        await interaction.response.send_message(f"{CHECK} ``Online. Pong!``")

    @commands.command(name="ping")
    async def ping_prefix(self, ctx):
        if not await verifyCommandPermissions(ctx):
            return
        await ctx.send(f"{CHECKWHITE} ``Online. Pong!``")

async def setup(bot):
    await bot.add_cog(General(bot))