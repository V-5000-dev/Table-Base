import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
import os
import logging
from enum import Enum

#logging setup------------------------------------------------
logging.basicConfig(
    filename="bot.log",
    level=logging.INFO,
    format="%(asctime)s %(message)s"
)
#setup------------------------------------------------
load_dotenv()

ERROR = "<:Error:1511925664910147607>"
CHECK = "<:CheckMark:1512108503857238076>"
X = "<:CrossMark:1511924485324804156>"
PERMISSON = "<:Permisson:1511924423819661442>"
MODIFICATION = "<:ModificationCommand:1511923491107246141>"
DANDER = "<:DangerCommand:1511923466016657438>"

GUILD_ID = discord.Object(id=1324223207536070697)


class CommandType(Enum):
    NORMAL = "Normal"
    MODIFICATION = "Modification"
    DANGER = "Danger"

NORMAL_LOG_CHANNEL = "1511534970533974026"
MODIFICATION_LOG_CHANNEL = "1511534970533974026"
DANGER_LOG_CHANNEL = "1511534970533974026"
LOG_CHANNELS = {
    CommandType.NORMAL: NORMAL_LOG_CHANNEL,
    CommandType.MODIFICATION: MODIFICATION_LOG_CHANNEL,
    CommandType.DANGER: DANGER_LOG_CHANNEL,
}



SEVER_ADMIN_ROLES = []
#Commands ------------------------------------------------

def verifyCommandPermissons(command_type: CommandType, *required_roles: list):
    async def predicate(interaction: discord.Interaction) -> bool:

        if not required_roles:
            allowed = True
        if interaction.user.guild_permissions.administrator:
            allowed = True
        
        if any(role_id in required_roles for role_id in user_role_ids):
            
            logging.info(f"{command_type.value}{interaction.command.name}{interaction.user}")
            allowed = False

        channel_id = LOG_CHANNELS[command_type]
        channel = interaction.client.get_channel(channel_id)

        if(channel):
            embed = discord.Embed(
                title=f"[{command_type.value}] Command Log",
                description=f"{interaction.user.mention} executed `{interaction.command.name}`" if allowed else f"{interaction.user.mention} attempted to and was denied from executing `{interaction.command.name}`",
                color = {
                CommandType.NORMAL: discord.Color.light_grey(),
                CommandType.MODIFICATION: discord.Color.orange(),
                CommandType.DANGER: discord.Color.red(),
                }[command_type]
                embed.add_field(name ="Staus", value = "Allowed" if allowed else "Denied")
                embed.add_field(name="User ID", value = interaction.user.id)
                await channel.send(embed=embed)

                if not allowed:
                    await interaction.response.send_message(f"{PERMISSON} You don't have permission to use this command.")
                
                return allowed
                    return app_commands.check(predicate)
                 
            )

        logging.info(f"[{interaction.command.name}] {interaction.user} ran command.")
        return app_commands.check(predicate)



    
        
        
                    

class Client(commands.Bot):
    async def setup_hook(self):
        try:
            self.tree.clear_commands(guild=GUILD_ID)
            synced = await self.tree.sync(guild=GUILD_ID)
            print(f"Synced {len(synced)} commands.")
        except Exception as e:
            print(f"Error syncing commands: {e}")

    async def on_ready(self):
        print(f'Logged in as {self.user}.')


intents = discord.Intents.default()
intents.message_content = True
bot = Client(command_prefix="db", intents=intents)

@bot.tree.command(name="ping", description="Checks if the application is online.", guild=GUILD_ID)
@verifyCommandPermissons(CommandType.NORMAL)
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(f"{CHECK} Online. Pong!")


@bot.tree.command(name="database-create", description="Create a new Database.", guild=GUILD_ID)
async def databaseCreate(interaction: discord.Interaction, name: str):
    await interaction.response.send_message(f"{CHECK} Online. Pong!")


bot.run('MTUxMTM5NjM0MzY4MjMwMjEyMg.GwWrS0.ZLAct5APdxXIkzlhIHBJK98MiEzXYe9jXbIEhg')