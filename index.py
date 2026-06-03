import discord
from dotenv import load_dotenv
import os

load_dotenv('file.env')

bot = discord.Bot()

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')

@bot.slash_command(name="ping", description="Check if this application is online.")
async def ping(ctx):
    await ctx.respond("Online. Pong!", ephemeral=True)


bot.run(os.getenv('TOKEN'))


