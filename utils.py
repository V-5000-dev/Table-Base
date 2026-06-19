import discord
import logging
import json
import config
from config import CommandType, PERMISSON
from discord import app_commands

SETTINGS_FILE = "settings.json"


def load_settings():
    """Load all guilds from JSON into memory."""
    try:
        with open(SETTINGS_FILE, "r") as f:
            data = json.load(f)

        for guild_id_str, guild_data in data.items():
            guild_id = int(guild_id_str)
            settings = config.get_guild(guild_id)

            settings["TABLE_REQUEST_CHANNEL_ID"] = guild_data.get("TABLE_REQUEST_CHANNEL_ID", 0)
            settings["TABLE_BACKUP_CHANNEL_ID"]  = guild_data.get("TABLE_BACKUP_CHANNEL_ID", 0)
            settings["SERVER_ADMIN_ROLE_IDS"]    = guild_data.get("SERVER_ADMIN_ROLE_IDS", [])
            settings["ADMIN_ROLE_IDS"]           = guild_data.get("ADMIN_ROLE_IDS", [])
            settings["MANAGER_ROLE_IDS"]         = guild_data.get("MANAGER_ROLE_IDS", [])
            settings["MEMBER_ROLE_IDS"]          = guild_data.get("MEMBER_ROLE_IDS", [])
            settings["LOG_UNSUCCESSFUL"]         = guild_data.get("LOG_UNSUCCESSFUL", True)
            settings["LOG_CHANNELS"][CommandType.USER]    = guild_data.get("USER_LOG_CHANNEL", 0)
            settings["LOG_CHANNELS"][CommandType.MANAGER] = guild_data.get("MANAGER_LOG_CHANNEL", 0)
            settings["LOG_CHANNELS"][CommandType.ADMIN]   = guild_data.get("ADMIN_LOG_CHANNEL", 0)
            settings["ALL_TABLES"]               = guild_data.get("ALL_TABLES", [])
            settings["COMMAND_PREFIX"]           = guild_data.get("COMMAND_PREFIX", "t! ")

    except FileNotFoundError:
        pass


def save_settings():
    """Save all guilds' settings to JSON."""
    try:
        with open(SETTINGS_FILE, "r") as f:
            data = json.load(f)
    except FileNotFoundError:
        data = {}

    for guild_id, settings in config.GUILD_SETTINGS.items():
        data[str(guild_id)] = {
            "TABLE_REQUEST_CHANNEL_ID": settings["TABLE_REQUEST_CHANNEL_ID"],
            "TABLE_BACKUP_CHANNEL_ID":  settings.get("TABLE_BACKUP_CHANNEL_ID", 0),
            "SERVER_ADMIN_ROLE_IDS":    settings["SERVER_ADMIN_ROLE_IDS"],
            "ADMIN_ROLE_IDS":           settings["ADMIN_ROLE_IDS"],
            "MANAGER_ROLE_IDS":         settings["MANAGER_ROLE_IDS"],
            "MEMBER_ROLE_IDS":          settings["MEMBER_ROLE_IDS"],
            "LOG_UNSUCCESSFUL":         settings["LOG_UNSUCCESSFUL"],
            "USER_LOG_CHANNEL":         settings["LOG_CHANNELS"][CommandType.USER],
            "MANAGER_LOG_CHANNEL":      settings["LOG_CHANNELS"][CommandType.MANAGER],
            "ADMIN_LOG_CHANNEL":        settings["LOG_CHANNELS"][CommandType.ADMIN],
            "ALL_TABLES":               settings["ALL_TABLES"],
            "COMMAND_PREFIX":           settings["COMMAND_PREFIX"],
        }

    with open(SETTINGS_FILE, "w") as f:
        json.dump(data, f, indent=4)


async def verifyCommandPermissions(ctx_or_interaction, command_type: CommandType = None, *required_roles) -> bool:
    if isinstance(ctx_or_interaction, discord.Interaction):
        user = ctx_or_interaction.user
        guild_permissions = ctx_or_interaction.user.guild_permissions
        command_name = ctx_or_interaction.command.name
        client = ctx_or_interaction.client
        guild_id = ctx_or_interaction.guild_id
    else:
        user = ctx_or_interaction.author
        guild_permissions = ctx_or_interaction.author.guild_permissions
        command_name = ctx_or_interaction.command.name
        client = ctx_or_interaction.bot
        guild_id = ctx_or_interaction.guild.id

    guild_settings = config.get_guild(guild_id)
    user_role_ids = [role.id for role in user.roles]

    if command_type is None:
        allowed = True
    elif guild_permissions.administrator:
        allowed = True
    elif any(role_id in required_roles for role_id in user_role_ids):
        allowed = True
    else:
        allowed = False

        # SERVER_ADMIN is a guild-level role, not per-table
        has_server_admin = any(r in guild_settings["SERVER_ADMIN_ROLE_IDS"] for r in user_role_ids)
        if has_server_admin:
            allowed = True
        elif command_type != CommandType.SERVER_ADMIN:
            # Table-specific role checks
            for table in guild_settings["ALL_TABLES"]:
                has_member  = any(r in table.get("member_role_ids",  []) for r in user_role_ids)
                has_manager = any(r in table.get("manager_role_ids", []) for r in user_role_ids)
                has_admin   = any(r in table.get("admin_role_ids",   []) for r in user_role_ids)

                if command_type == CommandType.USER    and (has_member or has_manager or has_admin):
                    allowed = True; break
                elif command_type == CommandType.MANAGER and (has_manager or has_admin):
                    allowed = True; break
                elif command_type == CommandType.ADMIN   and has_admin:
                    allowed = True; break

    # Respect LOG_UNSUCCESSFUL: skip logging denied attempts if the flag is off
    should_log = allowed or guild_settings["LOG_UNSUCCESSFUL"]

    if should_log:
        logging.info(
            f"[{command_type.value if command_type else 'NONE'}] [{command_name}] {user} "
            f"- {'Allowed' if allowed else 'Denied'}"
        )

    if command_type is not None and should_log:
        channel_id = guild_settings["LOG_CHANNELS"].get(command_type, 0)
        channel = client.get_channel(channel_id)
        if channel:
            embed = discord.Embed(
                title=f"[{command_type.value}] Command Log",
                description=(
                    f"{user.mention} executed `{command_name}`"
                    if allowed else
                    f"{user.mention} was denied from executing `{command_name}`"
                ),
                color={
                    CommandType.USER:         discord.Color.light_grey(),
                    CommandType.MANAGER:      discord.Color.orange(),
                    CommandType.ADMIN:        discord.Color.red(),
                    CommandType.SERVER_ADMIN: discord.Color.dark_red(),
                }[command_type]
            )
            embed.add_field(name="Status",    value="Allowed" if allowed else "Denied")
            embed.add_field(name="User ID",   value=user.id)
            embed.add_field(name="Timestamp", value=discord.utils.format_dt(discord.utils.utcnow()))

            embed.set_thumbnail(url={
                CommandType.USER:         "https://cdn.discordapp.com/emojis/1512608514919632896.png",
                CommandType.MANAGER:      "https://cdn.discordapp.com/emojis/1512608333394350301.png",
                CommandType.ADMIN:        "https://cdn.discordapp.com/emojis/1512608289819463762.png",
                CommandType.SERVER_ADMIN: "https://cdn.discordapp.com/emojis/1512608289819463762.png",
            }[command_type])

            await channel.send(embed=embed)

    if not allowed:
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.response.send_message(
                f"{PERMISSON} You don't have permission to use this command.", ephemeral=True
            )
        else:
            await ctx_or_interaction.send(f"{PERMISSON} You don't have permission to use this command.")

    return allowed


class PageView(discord.ui.View):
    def __init__(self, embeds, ctx_or_interaction, page_menus=None):
        super().__init__(timeout=60)
        self.embeds = embeds
        self.current_page = 0
        self.author_id = (
            ctx_or_interaction.user.id
            if isinstance(ctx_or_interaction, discord.Interaction)
            else ctx_or_interaction.author.id
        )
        self.page_menus = page_menus or {}
        self.dynamic_items = []

        for i, embed in enumerate(self.embeds):
            embed.set_footer(text=f"Page {i + 1} of {len(self.embeds)}")

        self.update_page_components()

    def update_page_components(self):
        for item in self.dynamic_items:
            self.remove_item(item)
        self.dynamic_items.clear()

        factories = self.page_menus.get(self.current_page, [])
        if callable(factories):
            factories = [factories]

        for factory in factories:
            new_item = factory()
            self.add_item(new_item)
            self.dynamic_items.append(new_item)

        self.prev_button.disabled = self.current_page == 0
        self.next_button.disabled = self.current_page == len(self.embeds) - 1

    async def refresh(self, interaction: discord.Interaction):
        self.update_page_components()
        await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.secondary)
    async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(f"{PERMISSON} ``You did not invoke this command.``", ephemeral=True)
            return
        self.current_page = max(0, self.current_page - 1)
        await self.refresh(interaction)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.secondary)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(f"{PERMISSON} ``You did not invoke this command.``", ephemeral=True)
            return
        self.current_page = min(len(self.embeds) - 1, self.current_page + 1)
        await self.refresh(interaction)


class SelectChannels_Menu(discord.ui.ChannelSelect):
    def __init__(self, callback_func, ctx_or_interaction):
        super().__init__(
            placeholder="Select a channel...",
            min_values=1,
            max_values=1,
            channel_types=[discord.ChannelType.text]
        )
        self.callback_func = callback_func
        self.allowed_user = (
            ctx_or_interaction.user
            if isinstance(ctx_or_interaction, discord.Interaction)
            else ctx_or_interaction.author
        )

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.allowed_user:
            await interaction.response.send_message(f"{PERMISSON} You did not invoke this command.", ephemeral=True)
            return
        await self.callback_func(interaction, self.values)


class SelectRoles_Menu(discord.ui.RoleSelect):
    def __init__(self, on_submit, ctx_or_interaction):
        super().__init__(
            placeholder="Select roles...",
            min_values=1,
            max_values=25
        )
        self.on_submit = on_submit
        self.allowed_user = (
            ctx_or_interaction.user
            if isinstance(ctx_or_interaction, discord.Interaction)
            else ctx_or_interaction.author
        )

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.allowed_user:
            await interaction.response.send_message(f"{PERMISSON} You did not invoke this command.", ephemeral=True)
            return
        await self.on_submit(interaction, self.values)


async def table_name_autocomplete(interaction: discord.Interaction, current: str):
    guild_settings = config.get_guild(interaction.guild_id)
    return [
        app_commands.Choice(name=t["name"], value=t["name"])
        for t in guild_settings["ALL_TABLES"]
        if current.lower() in t["name"].lower()
    ][:25]