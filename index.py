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

GUILD_ID = discord.Object(id=1324223207536070697)

intents = discord.Intents.default()
intents.message_content = True  # Fixed typo: messages_content -> message_content

bot = commands.Bot(command_prefix="db", intents=intents)
class Client(commands.Bot):
    async def setup_hook(self):
        await self.tree.sync(guild=GUILD_ID)
        print("Commands synced.")

    async def on_ready(self):
        print(f'{CHECK} Logged in as {self.user}.')


@bot.tree.command(name="ping", description="Checks if the application is online.", guild=GUILD_ID)
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(f"{CHECK} Online. Pong!")

bot.run(os.getenv('TOKEN'))