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


class DatabaseSelect(discord.ui.Select):
    def __init__(self, databases):
        options = [discord.SelectOption(label = name)]
@bot.bridge_command(name="database-settings", description="Configure a database's settings.")
async def database_setup(ctx, name: str):
    if name not in databases:
        await ctx.respond("<:Error:1511908546676265061> That database doesn't exist.")
        return
    cog = bot.cogs.get("DatabaseSetupPage")
    if cog is None:
        await ctx.respond("<:Error:1511908546676265061> Setup page not loaded.")
        return
    pages = cog.get_pages()
    embed = pages[1]

    await ctx.respond(embed = embed)

    


class DatabaseSetupPage(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        page_one_embed = discord.Embed(title="Page One", description="hello")
        page_one_embed.add_field(name="Example Field", value="Example Value", inline=False)

        self.pages = [
            "Page 1",
            page_one_embed
        ]

    def get_pages(self):
        return self.pages
        






@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    bot.add_cog(DatabaseSetupPage(bot))

bot.run(os.getenv('TOKEN'))