
import discord
from discord.ext import commands
from discord import app_commands
import os

ERROR = "<:Error:1511925664910147607>"
CHECK = "<:CheckMark:1512108503857238076>"
X = "<:CrossMark:1511924485324804156>"
PERMISSON = "<:Permisson:1511924423819661442>"
MODIFICATION = "<:ModificationCommand:1511923491107246141>"
DANDER = "<:DangerCommand:1511923466016657438>"

GUILD_ID = discord.object(id = 1324223207536070697)

class Client(discord.Client):
    async def on_ready(self):
        print(f'{CHECK} Logged in as {self.user}.')





intents = discord.Intents.default()
intents.messages_content = True

client = Client(command_prefix ="db", intents = intents)
client = Client(intents=intents)

@client.tree.command(name = "ping", description = "Checks if the application is online.", guild = GUILD_ID)
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(f"{CHECK} Online. Pong!")
        

client.run(os.getenv('TOKEN'))