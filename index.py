import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
import os
import logging
from enum import Enum
from datetime import datetime

# logging setup ------------------------------------------------
logging.basicConfig(
    filename="bot.log",
    level=logging.INFO,
    format="%(asctime)s %(message)s"
)

# setup ------------------------------------------------
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
    ALL = "All"
    USER = "User"
    MANAGER = "Manager"
    ADMIN = "Admin"


USER_LOG_CHANNEL = 0
MANAGER_LOG_CHANNEL = 0
ADMIN_LOG_CHANNEL = 0
LOG_CHANNELS = {
    CommandType.USER: USER_LOG_CHANNEL,
    CommandType.MANAGER: MANAGER_LOG_CHANNEL,
    CommandType.ADMIN: ADMIN_LOG_CHANNEL,
}

LOG_UNSUCCESSFUL = True

SERVER_ADMIN_ROLE_IDS = []
ADMIN_ROLE_IDS = []
MANAGER_ROLE_IDS = []
MEMBER_ROLE_IDS = []


# Commands ------------------------------------------------
class Client(commands.Bot):

    async def setup_hook(self):
        try:
            self.tree.copy_global_to(guild=GUILD_ID)
            synced = await self.tree.sync(guild=GUILD_ID)
            print(f"Synced {len(synced)} commands:")
            for cmd in synced:
                print(f"  - {cmd.name}")
        except Exception as e:
            print(f"Error syncing commands: {e}")

    async def on_ready(self):
        print(f"Logged in as {self.user}.")
        print("Commands currently in tree:")
        for cmd in self.tree.walk_commands():
            print(f"  - {cmd.name}")


intents = discord.Intents.default()
intents.message_content = True
client = Client(command_prefix="db ", intents=intents)

async def verifyCommandPermissions(ctx_or_interaction, command_type: CommandType = None) -> bool:
    if isinstance(ctx_or_interaction, discord.Interaction):
        user = ctx_or_interaction.user
        guild_permissions = ctx_or_interaction.user.guild_permissions
        command_name = ctx_or_interaction.command.name
        _client = ctx_or_interaction.client
    else:
        user = ctx_or_interaction.author
        guild_permissions = ctx_or_interaction.author.guild_permissions
        command_name = ctx_or_interaction.command.name
        _client = ctx_or_interaction.bot

    user_role_ids = [role.id for role in user.roles]

    allowed_roles = []
    
    if command_type == CommandType.USER:
        allowed_roles += MEMBER_ROLE_IDS
    if command_type in (CommandType.USER, CommandType.MANAGER):
        allowed_roles += MANAGER_ROLE_IDS
    if command_type in (CommandType.USER, CommandType.MANAGER, CommandType.ADMIN):
        allowed_roles += ADMIN_ROLE_IDS
    allowed_roles += SERVER_ADMIN_ROLE_IDS
    if command_type is None:
        return True
    if guild_permissions.administrator:
        allowed = True
    elif allowed_roles:
        allowed = True
    elif any(role_id in allowed_roles for role_id in user_role_ids):
        allowed = True
    else:
        allowed = False

    logging.info(f"[{command_type.value}] [{command_name}] {user} - {'Allowed' if allowed else 'Denied'}")

    channel_id = LOG_CHANNELS[command_type]
    channel = _client.get_channel(channel_id) if isinstance(channel_id, int) and channel_id != 0 else None

    if channel and (allowed or LOG_UNSUCCESSFUL):
        embed = discord.Embed(
            title=f"[{command_type.value}] Unsuccessful Command Log" if not allowed else f"[{command_type.value}] Command Log",
            description=(
                f"{user.mention} was denied from executing `{command_name}`"
                if not allowed
                else f"{user.mention} executed `{command_name}`"
            ),
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
            await ctx_or_interaction.response.send_message(
                f"{PERMISSON} ``You don't have permission to use this command.``"
            )
        else:
            await ctx_or_interaction.send(f"{PERMISSON} ``You don't have permission to use this command.``")

    return allowed

# -----------------------------------------------------------------
class PageView(discord.ui.View):
    def __init__(self, embeds, ctx_or_interaction: int, page_menus=None):
        super().__init__(timeout=60)
        self.embeds = embeds
        self.current_page = 0
        self.author_id  = (
            ctx_or_interaction.user.id
            if isinstance(ctx_or_interaction, discord.Interaction)
            else ctx_or_interaction.author.id
        )
        self.page_menus = page_menus or {}

        for i, embed in enumerate(self.embeds):
            embed.set_footer(text=f"Page {i + 1} of {len(self.embeds)}")

        self.update_page_components()
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                f"{PERMISSON} ``You cannot interact with other people's embeds.``", ephemeral=True
            )
            return False
        return True

    def update_page_components(self):
        for item in list(self.children):
            if not isinstance(item, discord.ui.Button):
                self.remove_item(item)

        factories = self.page_menus.get(self.current_page, [])

        if callable(factories):
            factories = [factories]

        for factory in factories:
            self.add_item(factory())

    async def refresh(self, interaction: discord.Interaction):
        self.update_page_components()
        await interaction.response.edit_message(
            embed=self.embeds[self.current_page],
            view=self
        )

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.secondary)
    async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = max(0, self.current_page - 1)
        await self.refresh(interaction)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.secondary)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = min(len(self.embeds) - 1, self.current_page + 1)
        await self.refresh(interaction)


# -----------------------------------------------------------------
class SelectChannels_MenuView(discord.ui.View):
    def __init__(self, channels: list[discord.TextChannel], on_submit):
        super().__init__(timeout=None)
        self.add_item(SelectChannels_Menu(channels, on_submit))


class SelectChannels_Menu(discord.ui.Select):
    def __init__(self, channels: list[discord.TextChannel], on_submit):
        self.on_submit = on_submit

        options = [
            discord.SelectOption(
                label=channel.name,
                value=str(channel.id)
            )
            for channel in channels[:25]
        ]

        super().__init__(
            placeholder="Select a channel...",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        guild = interaction.guild
        selected_channels = [
            guild.get_channel(int(ch_id))
            for ch_id in self.values
        ]
        selected_channels = [c for c in selected_channels if c]
        await self.on_submit(interaction, selected_channels)


# -----------------------------------------------------------------
class SelectRoles_MenuView(discord.ui.View):
    def __init__(self, roles: list[discord.Role], on_submit):
        super().__init__()
        self.add_item(SelectRoles_Menu(roles, on_submit))


class SelectRoles_Menu(discord.ui.Select):
    def __init__(self, roles, on_submit):
        self.on_submit = on_submit

        options = [
            discord.SelectOption(
                label=role.name,
                value=str(role.id)
            )
            for role in roles[:25]
        ]

        super().__init__(
            placeholder="Select roles...",
            min_values=1,
            max_values=len(options),
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        selected_roles = [
            interaction.guild.get_role(int(role_id))
            for role_id in self.values
        ]
        selected_roles = [r for r in selected_roles if r]
        await self.on_submit(interaction, selected_roles)


# -----------------------------------------------------------------
async def ping_logic(ctx_or_interaction):
    if not await verifyCommandPermissions(ctx_or_interaction):
        return
    if isinstance(ctx_or_interaction, discord.Interaction):
        await ctx_or_interaction.response.send_message(f"{CHECK} ``Online. Pong!``")
    else:
        await ctx_or_interaction.send(f"{CHECK} ``Online. Pong!``")


@client.tree.command(name="ping", description="Checks if the application is online.", guild=GUILD_ID)
async def ping(interaction: discord.Interaction):
    await ping_logic(interaction)


@client.command(name="ping")
async def ping_prefix(ctx):
    await ping_logic(ctx)


# -----------------------------------------------------------------
async def databaseCreate_logic(ctx_or_interaction):
    if not await verifyCommandPermissions(ctx_or_interaction, CommandType.MANAGER, *MANAGER_ROLE_IDS):
        return
    if isinstance(ctx_or_interaction, discord.Interaction):
        await ctx_or_interaction.response.send_message(f"{CHECK} Test!")
    else:
        await ctx_or_interaction.send(f"{CHECK} Test!")


@client.tree.command(name="database-create", description="Create a new Database.", guild=GUILD_ID)
async def databaseCreate(interaction: discord.Interaction):
    await databaseCreate_logic(interaction)


@client.command(name="database-create")
async def databaseCreate_prefix(ctx):
    await databaseCreate_logic(ctx)


# -----------------------------------------------------------------
async def serverSettings_logic(ctx_or_interaction):
    if not await verifyCommandPermissions(ctx_or_interaction, CommandType.ADMIN, *ADMIN_ROLE_IDS):
        return

    guild = ctx_or_interaction.guild if not isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.guild

    embeds = [
        discord.Embed(
            title="Server Settings - Administration Permissions",
            description=(
                "Select which role(s) should have application-wide administration permissions. "
                "Users with these roles automatically receive admin permissions in all databases, "
                "and can create and delete databases. Roles that have Discord's administration "
                "permission enabled will also have this permission."
            )
        ),
        discord.Embed(
            title="Server Settings - User Log Channels",
            description="Select which channel should receive logs for unprotected user commands. Leaving this empty will prevent user commands from being logged."
        ),
        discord.Embed(
            title="Server Settings - Management Log Channels",
            description="Select which channel should receive logs for protected database management commands. Leaving this empty will prevent database management commands from being logged."
        ),
        discord.Embed(
            title="Server Settings - Administrative Log Channels",
            description="Select which channel should receive logs for protected database admin and server commands. Leaving this empty will prevent admin commands from being logged."
        ),
        discord.Embed(
            title="Server Settings - Logging Settings",
            description="Toggle whether unsuccessful command logs from unauthorized users should be logged."
        )
    ]

    view = PageView(
        embeds=embeds,
        ctx_or_interaction=ctx_or_interaction,
        page_menus={
            0: [lambda: SelectRoles_Menu(guild.roles, save_serveradmin_roles)],
            1: [lambda: SelectChannels_Menu(guild.text_channels, set_user_log_channel)],
            2: [lambda: SelectChannels_Menu(guild.text_channels, set_manager_log_channel)],
            3: [lambda: SelectChannels_Menu(guild.text_channels, set_admin_log_channel)],
            4: [lambda: ToggleLoggingButton()],
        }
    )

    if isinstance(ctx_or_interaction, discord.Interaction):
        await ctx_or_interaction.response.send_message(embed=embeds[0], view=view)
    else:
        await ctx_or_interaction.send(embed=embeds[0], view=view)


@client.tree.command(name="server-settings", description="Configure server settings.", guild=GUILD_ID)
async def serverSettings(interaction: discord.Interaction):
    await serverSettings_logic(interaction)

async def serverSettings_prefix(ctx):
    await serverSettings_logic(ctx)


class ToggleLoggingButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Disable logs from unsuccessful command attempts", style=discord.ButtonStyle.grey)
        self.state = False

    async def callback(self, interaction: discord.Interaction):
        global LOG_UNSUCCESSFUL
        self.state = not self.state
        LOG_UNSUCCESSFUL = not self.state
        self.label = "Enable logs from unsuccessful command attempts" if self.state else "Disable logs from unsuccessful command attempts"
        await interaction.response.edit_message(view=self.view)


async def save_serveradmin_roles(interaction, roles):
    global SERVER_ADMIN_ROLE_IDS
    SERVER_ADMIN_ROLE_IDS = [r.id for r in roles]
    await interaction.response.send_message(
        f"{CHECK} ``Saved admin roles: {', '.join(r.name for r in roles)}``",
        ephemeral=True
    )

async def set_user_log_channel(interaction, channels):
    if not channels:
        return
    LOG_CHANNELS[CommandType.USER] = channels[0].id
    await interaction.response.send_message(
        f"{CHECK} ``User log channel set to: {channels[0].mention}``",
        ephemeral=True
    )


async def set_manager_log_channel(interaction, channels):
    if not channels:
        return
    LOG_CHANNELS[CommandType.MANAGER] = channels[0].id
    await interaction.response.send_message(
        f"{CHECK} ``Manager log channel set to: {channels[0].mention}``",
        ephemeral=True
    )


async def set_admin_log_channel(interaction, channels):
    if not channels:
        return
    LOG_CHANNELS[CommandType.ADMIN] = channels[0].id
    await interaction.response.send_message(
        f"{CHECK} ``Admin log channel set to: {channels[0].mention}``",
        ephemeral=True
    )


# -----------------------------------------------------------------
client.run(os.getenv('TOKEN'))