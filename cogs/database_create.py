import discord
from discord.ext import commands
from discord import app_commands
from config import GUILD_ID, CHECK, CommandType
from utils import verifyCommandPermissions

class Database(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="database-create", description="Create a new Database.")
    async def database_create(self, interaction: discord.Interaction):
        if not await verifyCommandPermissions(interaction, CommandType.MANAGER):
            return
        await interaction.response.send_message(f"{CHECK} Test!")

    @commands.command(name="database-create")
    async def database_create_prefix(self, ctx):
        if not await verifyCommandPermissions(ctx, CommandType.MANAGER):
            return
        await ctx.send(f"{CHECK} Test!")

async def setup(bot):
    await bot.add_cog(Database(bot))