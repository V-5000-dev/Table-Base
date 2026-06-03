import discord
from discord.ext import bridge
from discord.ext import commands
from dotenv import load_dotenv
import os

load_dotenv('file.env')
intents = discord.Intents.default()
intents.message_content = True
bot = bridge.Bot(command_prefix='d!', intents=intents)
#commands
#ping
@bot.bridge_command(description="Check if the bot is online.")
async def ping(ctx):
    await ctx.respond('Online. Pong!')

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
bot.run(os.getenv('TOKEN'))


