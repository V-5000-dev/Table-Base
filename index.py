import asyncio
import discord
from discord.ext import bridge
from discord.commands import SlashCommandGroup
from discord.ext import commands, pages
from dotenv import load_dotenv
import os
import json

DB_FILE = 'databases.json'

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
    await ctx.respond('Online. Pong!')


@bot.bridge_command(name="database-create", description="Create a database.")
async def database_create(ctx, name: str):
    if name in databases:
        await ctx.respond("⚠️ A database with that name already exists.")
        return
    databases[name] = {
        'database_admins': [],
        'database_managers': [],
        'database_members': [],
        'database_data': []
    }
    save_databases()
    await ctx.respond(f"Database `{name}` created!")


@bot.bridge_command(name="database-settings", description="Configure a database's settings.")
async def database_setup(ctx, name: str):
    if name not in databases:
        await ctx.respond("⚠️ That database doesn't exist.")
        return
    embed = discord.Embed(
        title="Database Permissions",
        description="Select a role to give Admin access."
    )


class DatabaseSetupPage(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.pages = [
            "Page 1",
            [
                discord.embed(title = "Page One", text = "hello")
            ]
        ]
        self.pages[1].add_field(
            name = "Example Field", value = "Example Value", inline = False
        )
        def get_pages(self):
            return self.pages
        
        databaseSetupPage = SlashCommandGroup("database-settings", "Configure a database's settings.")







@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')

bot.run(os.getenv('TOKEN'))