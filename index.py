import discord
from discord.ext import commands
from dotenv import load_dotenv
import os

load_dotenv('file.env')

bot = discord.Bot()
bot = commands.Bot(command_prefix='d!')

#Commands
#Ping
@bot.event
async def ping(ctx):
    return 'Pong!'

@bot.command()
async def ping(ctx):
    await ctx.send(await ping(ctx))

@bot.slash_command(name="ping")
async def ping_slash(ctx):
    await ctx.respond(await ping(ctx))




bot.run(os.getenv('TOKEN'))


