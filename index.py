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

class /(discord.ui.Select):
    def __init__(self, databases):
        options = [
            discord.SelectOption(label=db_name, value=db_name)
            for db_name in databases
        ]
        super().__init__(placeholder="Choose a database...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        selected_db = self.values[0]  # ✅ Indented inside callback

        cog = interaction.client.cogs.get("DatabaseSetupPage")  # ✅ Indented inside callback
        if cog is None:
            await interaction.response.send_message(f"{ERROR} Setup page not loaded.")
            return

        pages = cog.get_pages()  # ✅ Indented inside callback
        embed = pages[1]

        await interaction.response.send_message(f"Settings for **{selected_db}**", embed=embed, ephemeral=True)
    

@bot.bridge_command(name="database-settings", description="Configure a database's settings.")
async def database_setup(ctx):  # Removed `name` parameter
    if not databases:
        await ctx.respond(f"{ERROR} No databases found.")
        return

    view = DatabaseSelectView(databases)
    await ctx.respond("Select a database to configure:", view=view)

 

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