import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
import os
import logging
from enum import Enum
from datetime import datetime

#logging setup------------------------------------------------
logging.basicConfig(
    filename="bot.log",
    level=logging.INFO,
    format="%(asctime)s %(message)s"
)
#setup------------------------------------------------
load_dotenv(dotenv_path=".env")

ERROR = "<:Error:1511925664910147607>"
CHECK = "<:CheckMark:1512108503857238076>"
CHECKWHITE = "<:CheckMark2:1512309496947413012>"
X = "<:CrossMark:1511924485324804156>"
PERMISSON = "<:Permisson:1511924423819661442>"
MODIFICATION = "<:ModificationCommand:1511923491107246141>"
DANDER = "<:DangerCommand:1511923466016657438>"

GUILD_ID = discord.Object(id=1324223207536070697)


class CommandType(Enum):
    SAFE = "Safe"
    MODIFICATION = "Modification"
    DANGER = "Danger"

SAFE_LOG_CHANNEL = 1511534970533974026
MODIFICATION_LOG_CHANNEL = 1511534970533974026
DANGER_LOG_CHANNEL = 1511534970533974026
LOG_CHANNELS = {
    CommandType.SAFE: SAFE_LOG_CHANNEL,
    CommandType.MODIFICATION: MODIFICATION_LOG_CHANNEL,
    CommandType.DANGER: DANGER_LOG_CHANNEL,
}



SEVER_ADMIN_ROLES = []
#Commands ------------------------------------------------
class Client(commands.Bot):

    async def setup_hook(self):
        try:
     #      self.tree.clear_commands(guild=GUILD_ID)
        #    await self.tree.sync(guild=GUILD_ID)

            self.tree.copy_global_to(guild=GUILD_ID)
            synced = await self.tree.sync(guild=GUILD_ID)
            print(f"Synced {len(synced)} commands:")
            for cmd in synced:
                print(f"  - {cmd.name}")
        except Exception as e:
            print(f"Error syncing commands: {e}")

    async def on_ready(self):
        print(f"Logged in as {self.user}.")


intents = discord.Intents.default()
intents.message_content = True
client = Client(command_prefix = "db ", intents = intents)

async def on_message(message):
    if message.author == client.user:
        return
    await client.process_commands(message)


async def on_ready(self):
    print(f"Logged in as {self.user}.")
    print("Commands currently in tree:")
    for cmd in self.tree.walk_commands():
        print(f"  - {cmd.name}")



async def verifyCommandPermissions(ctx_or_interaction, command_type: CommandType, *required_roles) -> bool:
    if isinstance(ctx_or_interaction, discord.Interaction):
        user = ctx_or_interaction.user
        guild_permissions = ctx_or_interaction.user.guild_permissions
        command_name = ctx_or_interaction.command.name
        client = ctx_or_interaction.client
    else:
        user = ctx_or_interaction.author
        guild_permissions = ctx_or_interaction.author.guild_permissions
        command_name = ctx_or_interaction.command.name
        client = ctx_or_interaction.bot

    user_role_ids = [role.id for role in user.roles]

    if not required_roles:
        allowed = True
    elif guild_permissions.administrator:
        allowed = True
    elif any(role_id in required_roles for role_id in user_role_ids):
        allowed = True
    else:
        allowed = False

    logging.info(f"[{command_type.value}] [{command_name}] {user} - {'Allowed' if allowed else 'Denied'}")

    channel_id = LOG_CHANNELS[command_type]
    channel = client.get_channel(channel_id)
    if channel:
        embed = discord.Embed(
            title=f"[{command_type.value}] Command Log",
            description=f"{user.mention} executed `{command_name}`" if allowed else f"{user.mention} was denied from executing `{command_name}`",
            color={
                CommandType.SAFE: discord.Color.light_grey(),
                CommandType.MODIFICATION: discord.Color.orange(),
                CommandType.DANGER: discord.Color.red(),
            }[command_type],

            

        )

        embed.add_field(name="Status", value="Allowed" if allowed else "Denied")
        embed.add_field(name="User ID", value=user.id)
        embed.add_field(name="Timestamp", value=discord.utils.format_dt(discord.utils.utcnow()))
        thumbnails = {
            CommandType.SAFE: "https://cdn.discordapp.com/emojis/1512309496947413012.png",
            CommandType.MODIFICATION: "https://cdn.discordapp.com/emojis/1511923491107246141.png",
            CommandType.DANGER: "https://cdn.discordapp.com/emojis/1511923466016657438.png",
        }
        embed.set_thumbnail(url=thumbnails[command_type])
        await channel.send(embed=embed)

    if not allowed:
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.response.send_message(f"{PERMISSON} You don't have permission to use this command.", ephemeral=True)
        else:
            await ctx_or_interaction.send(f"{PERMISSON} You don't have permission to use this command.")

    return allowed

@client.event
async def ping_logic(ctx_or_interaction):
    if not await verifyCommandPermissions(ctx_or_interaction, CommandType.SAFE):
        return
    if isinstance(ctx_or_interaction, discord.Interaction):
        await ctx_or_interaction.response.send_message(f"{CHECK} Online. Pong!")
    else:
        await ctx_or_interaction.send(f"{CHECK} Online. Pong!")

@client.tree.command(name="ping", description="Checks if the application is online.", guild=GUILD_ID)
async def ping(interaction: discord.Interaction):
    await ping_logic(interaction)
@client.command(name="ping")
async def ping_prefix(ctx):
    await ping_logic(ctx)
#-----------------------------------------------------------------
@client.tree.command(name="database-create", description="Create a new Database.", guild=GUILD_ID)
async def databaseCreate(interaction: discord.Interaction, name: str):
    await interaction.response.send_message(f"{CHECK} Online. Pong!")


client.run(os.getenv('TOKEN'))