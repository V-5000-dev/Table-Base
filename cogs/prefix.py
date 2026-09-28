import discord
import config
from discord.ext import commands
from discord import app_commands
from config import CHECK


class Prefix(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_prefix_text(self, guild):
        if guild is None:
            return "t! "
        return config.get_guild(guild.id)["COMMAND_PREFIX"]

    @app_commands.command(name="prefix", description="Show the bot's command prefix for this server.")
    async def prefix(self, interaction: discord.Interaction):
        prefix = self.get_prefix_text(interaction.guild)
        await interaction.response.send_message(f"{CHECK} ``Prefix:`` ``{prefix}``", ephemeral=True)

    @commands.command(name="prefix")
    async def prefix_prefix(self, ctx):
        prefix = self.get_prefix_text(ctx.guild)
        await ctx.send(f"{CHECK} ``Prefix:`` ``{prefix}``")


async def setup(bot):
    await bot.add_cog(Prefix(bot))