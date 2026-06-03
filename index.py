import discord
from discord.ext import bridge
from discord.ext import commands
from dotenv import load_dotenv
import os

load_dotenv('file.env')
intents = discord.Intents()
intents.message_content = True
bot = bridge.Bot(command_prefix='d!', intents=intents)
#commands
#ping----------------------------------------------------------------------------------------
async def ping_logic():
    return 'Online. Pong!'
@bot.bridge_command()
async def ping(ctx):
    await ctx.send(await ping_logic())



@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
bot.run(os.getenv('TOKEN'))


