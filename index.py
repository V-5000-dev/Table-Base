import discord
from discord.ext import bridge
from discord.ext import commands
from dotenv import load_dotenv
import os
import json
import os

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

# remove the "bool" line

bool 
#commands
#ping
@bot.bridge_command(name = "ping", description="Check if the bot is online.")
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
    await ctx.respond(f"Database `{name}` created!")  # fix: use f-string


@bot.bridge_command(name="database-setup", description="Configure a database's settings.")
async def database_setup(ctx, name: str):
    if name not in databases:
        await ctx.respond("⚠️ That database doesn't exist.")
        return
    embed = discord.Embed(title="Database Permissions", description="Select a role to give Admin access.")
    await ctx.respond(embed=embed, view=DataBaseAdminRoleSelect(name))


class DataBaseAdminRoleSelect(discord.ui.View):
    def __init__(self, name):
        super().__init__()
        self.name = name
        self.add_item(DataBaseAdminDropdown(name))


class DataBaseAdminDropdown(discord.ui.RoleSelect):
    def __init__(self, name):
        super().__init__(placeholder="Select a role...")
        self.name = name

    async def callback(self, interaction: discord.Interaction): 
        role = self.values[0]
        databases[self.name]['database_admins'].append(str(role.id))
        save_databases()
        await interaction.response.send_message(f"`{role.name}` set as Admin!", ephemeral=True)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
bot.run(os.getenv('TOKEN'))


