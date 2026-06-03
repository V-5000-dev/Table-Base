import discord
from discord.ext import commands
from dotenv import load_dotenv
import os

load_dotenv('file.env')

bot = commands.Bot(command_prefix='d!')

#commands
#ping
async def ping_logic():
    return 'Pong!'
@bot.command()
async def ping(ctx):
    await ctx.send(await ping_logic())
@bot.slash_command(name="ping", description="Check if the application is online.")
async def ping_slash(ctx):
    await ctx.respond(await ping_logic())


@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
bot.run(os.getenv('TOKEN'))


