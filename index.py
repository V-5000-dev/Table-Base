import asyncio
import discord
from discord.ext import bridge
from discord.commands import SlashCommandGroup
from discord.ext import commands, pages
from dotenv import load_dotenv
import os
import json

DB_FILE = 'databases.json'
#Emojis
ERROR = "<:Error:1511925664910147607>"
CHECK = "<:CheckMark:1511961188848631838>"
X = "<:CrossMark:1511924485324804156>"
PERMISSON = "<:Permisson:1511924423819661442>"
MODIFICATION = "<:ModificationCommand:1511923491107246141>"
DANDER = "<:DangerCommand:1511923466016657438>"

def load_databases():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_databases():
    with open(DB_FILE, 'w') as f:
        json.dump(databases, f)


load_dotenv('file.env')
databases = load_databases()

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.presences = True

bot = bridge.Bot(command_prefix='d!', intents=intents)


@bot.bridge_command(name="ping", description="Check if the bot is online.")
async def ping(ctx):
    await ctx.respond(f'{CHECK} Online. Pong!')




@bot.bridge_command(name="database-create", description="Create a database.")
async def database_create(ctx, name: str):
    if name in databases:
        await ctx.respond(f"{ERROR} A database with that name already exists.")
        return
    databases[name] = {
        'database_admins': [],
        'database_managers': [],
        'database_members': [],
        'database_data': []
    }
    save_databases()
    await ctx.respond(f"{CHECK} Database `{name}` created!")
    
@bot.bridge_command(name= "server-settings" desription = "Configure the bot's settings for the server.")
async def printer(interaction: discord.Interaction):
    embed = discord.embed(title = "DataBase Server Settings", desription =  "Configure the server settings below.")
    await interaction.response.send_message(embed=embed)








@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')

bot.run(os.getenv('TOKEN'))