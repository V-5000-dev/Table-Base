import discord
from discord.ext import commands
from discord import app_commands
from config import CHECK


class Ping(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="ping", description="Check the bot's latency.")
    async def ping(self, interaction: discord.Interaction):
        latency = round(self.bot.latency * 1000)
        await interaction.response.send_message(f"{CHECK} `Online. `Pong!`` ``{latency}ms``", ephemeral=True)

    @commands.command(name="ping")
    async def ping_prefix(self, ctx):
        latency = round(self.bot.latency * 1000)
        await ctx.send(f"{CHECK} ``Online. Pong!`` ``{latency}ms``")


async def setup(bot):
    await bot.add_cog(Ping(bot))