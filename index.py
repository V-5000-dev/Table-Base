import discord
from discord.ext import commands
from dotenv import load_dotenv
import os

load_dotenv('file.env')

bot = commands.Bot(command_prefix='d!')

#commands
#ping
async def ping():
    return 'Pong!'
@bot.command()
async def ping_prefix(ctx):
    await ctx.send(await ping())
@bot.slash_command(name="ping", description="Replies with Pong!")
async def ping_slash(ctx):
    await ctx.respond(await ping())


@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
bot.run(os.getenv('TOKEN'))


