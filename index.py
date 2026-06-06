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
USER = "<:UserCommand:1512608514919632896>"
MANAGER = "<:ManagerCommand:1512608333394350301>"
ADMIN = "<:AdminCommand:1512608289819463762>"

GUILD_ID = discord.Object(id=1324223207536070697)


class CommandType(Enum):
    USER = "User"
    MANAGER = "Manager"
    ADMIN = "Admin"

USER_LOG_CHANNEL = 1511534970533974026
MANAGER_LOG_CHANNEL = 1511534970533974026
ADMIN_LOG_CHANNEL = 1511534970533974026
LOG_CHANNELS = {
    CommandType.USER: USER_LOG_CHANNEL,
    CommandType.MANAGER: MANAGER_LOG_CHANNEL,
    CommandType.ADMIN: ADMIN_LOG_CHANNEL,
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
                CommandType.USER: discord.Color.light_grey(),
                CommandType.MANAGER: discord.Color.orange(),
                CommandType.ADMIN: discord.Color.red(),
            }[command_type],

            

        )

        embed.add_field(name="Status", value="Allowed" if allowed else "Denied")
        embed.add_field(name="User ID", value=f"``{user.id}``")
        embed.add_field(name="Timestamp", value=discord.utils.format_dt(discord.utils.utcnow()))
        thumbnails = {
            CommandType.USER: "https://cdn.discordapp.com/emojis/1512608514919632896.png",
            CommandType.MANAGER: "https://cdn.discordapp.com/emojis/1512608333394350301.png",
            CommandType.ADMIN: "https://cdn.discordapp.com/emojis/1512608289819463762.png",
        }
        embed.set_thumbnail(url=thumbnails[command_type])
        await channel.send(embed=embed)

    if not allowed:
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.response.send_message(f"{PERMISSON} You don't have permission to use this command.", ephemeral=True)
        else:
            await ctx_or_interaction.send(f"{PERMISSON} You don't have permission to use this command.")

    return allowed

class PageView(discord.ui.View):
    def __init__(self, embeds: list[discord.Embed], roles: list[discord.Role]):
        super().__init__(timeout=60)
        self.embeds = embeds
        self.current_page = 0
        self.roles = roles

        for i, embed in enumerate(self.embeds):
            embed.set_footer(text=f"Page {i+1} of {len(self.embeds)}")

        self.prev_button.disabled = True
        if len(embeds) == 1:
            self.next_button.disabled = True

        # Add the dropdown for page 0 on init
        self.update_select()

    def update_buttons(self):
        self.prev_button.disabled = self.current_page == 0
        self.next_button.disabled = self.current_page == len(self.embeds) - 1

    def update_select(self):

        for item in self.children.copy():
            if isinstance(item, discord.ui.Select):
                self.remove_item(item)


        if self.current_page == 0:
            self.add_item(SelectRoles_Menu(self.roles))

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.secondary)
    async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page -= 1
        self.update_buttons()
        self.update_select()
        await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.secondary)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page += 1
        self.update_buttons()
        self.update_select()
        await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)

class SelectRoles_MenuView(discord.ui.View):
    def __init__(self, roles: list[discord.Role]):
        super().__init__()
        self.add_item(SelectRoles_Menu(roles))
class SelectRoles_Menu(discord.ui.Select):
    def __init__(self, roles: list[discord.Role]):

        options = [
            discord.SelectOption(
                label=f"{role.name} ({role.id})",
                value=str(role.id),
            )
            for role in roles
            if not role.is_default()
        ][:25]

        print(f"Options built: {options}")
        if not options:
            options = [discord.SelectOption(label="No roles available", value="none")]
        super().__init__(
            placeholder="Select a role..",
            min_values=1,
            max_values=len(options), 
            options=options
        )
                

#-----------------------------------------------------------------
@client.event
async def ping_logic(ctx_or_interaction):
    if not await verifyCommandPermissions(ctx_or_interaction, CommandType.USER):
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
@client.event
async def databaseCreate_logic(ctx_or_interaction):
    if not await verifyCommandPermissions(ctx_or_interaction, CommandType.MANAGER):
        return
    if isinstance(ctx_or_interaction, discord.Interaction):
        await ctx_or_interaction.response.send_message(f"{CHECK} Test!")
    else:
        await ctx_or_interaction.send(f"{CHECK} Test!")
@client.tree.command(name="database-create", description="Create a new Database.", guild=GUILD_ID)
async def databaseCreate(interaction: discord.Interaction):
    await databaseCreate_logic(interaction)
@client.command(name="database create")
async def databaseCreate_prefix(ctx):
    await databaseCreate_logic(ctx)
 #-----------------------------------------------------------------

    async def callback(self, interaction: discord.Interaction):
        role_id = int(self.values[0])
        role = interaction.guild.get_role(role_id)
        await interaction.response.send_message(f"You selected: {role.mention}")


async def serverSettings_logic(ctx_or_interaction):
    if not await verifyCommandPermissions(ctx_or_interaction, CommandType.ADMIN):
        return

    embeds = [
        discord.Embed(
            title="Server Settings - Administration Permissions",
            description="Select which role(s) should have administration permissions..."
        ),
        discord.Embed(
            title="Test",
            description="Page 2 content here."
        )
    ]

    if isinstance(ctx_or_interaction, discord.Interaction):
        guild = ctx_or_interaction.guild
        view = PageView(embeds, guild.roles)
        await ctx_or_interaction.response.send_message(embed=embeds[0], view=view)

    else:
        view = PageView(embeds, ctx_or_interaction.guild.roles)
        await ctx_or_interaction.send(embed=embeds[0], view=view)
    view = PageView(embeds)
    if isinstance(ctx_or_interaction, discord.Interaction):
        guild = ctx_or_interaction.guild
        print(f"Roles found: {guild.roles}")
        view = SelectRoles_MenuView(guild.roles)
        await ctx_or_interaction.response.send_message(embed=embeds[0], view=view)

        await ctx_or_interaction.response.send_message(view=view)

        
    else:
        await ctx_or_interaction.send(embed=embeds[0], view=view)
        await ctx_or_interaction.send(f"{CHECK} Test!")
@client.tree.command(name="server-settings", description="Create a new Database.", guild=GUILD_ID)
async def serverSettings(interaction: discord.Interaction):
    await serverSettings_logic(interaction)
@client.command(name="server settings")
async def databaseCreate_prefix(ctx):
    await serverSettings_logic(ctx)



client.run(os.getenv('TOKEN'))