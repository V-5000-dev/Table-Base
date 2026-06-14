import discord
import logging
import json
import config
from config import CommandType, GUILD_ID, PERMISSON
from discord import app_commands

SETTINGS_FILE = "settings.json"

def load_settings():
    try:
        with open(SETTINGS_FILE, "r") as f:
            data = json.load(f)
        config.TABLE_REQUEST_CHANNEL_ID = data.get("TABLE_REQUEST_CHANNEL_ID", 0)
        config.SERVER_ADMIN_ROLE_IDS = data.get("SERVER_ADMIN_ROLE_IDS", [])
        config.ADMIN_ROLE_IDS        = data.get("ADMIN_ROLE_IDS", [])
        config.MANAGER_ROLE_IDS      = data.get("MANAGER_ROLE_IDS", [])
        config.MEMBER_ROLE_IDS       = data.get("MEMBER_ROLE_IDS", [])
        config.LOG_UNSUCCESSFUL      = data.get("LOG_UNSUCCESSFUL", True)
        config.LOG_CHANNELS[CommandType.USER]    = data.get("USER_LOG_CHANNEL", 0)
        config.LOG_CHANNELS[CommandType.MANAGER] = data.get("MANAGER_LOG_CHANNEL", 0)
        config.LOG_CHANNELS[CommandType.ADMIN]   = data.get("ADMIN_LOG_CHANNEL", 0)
        config.ALL_TABLES = data.get('ALL_TABLES', [])
    except FileNotFoundError:
        pass

def save_settings():
    data = {
        "TABLE_REQUEST_CHANNEL_ID": config.TABLE_REQUEST_CHANNEL_ID,
        "SERVER_ADMIN_ROLE_IDS": config.SERVER_ADMIN_ROLE_IDS,
        "ADMIN_ROLE_IDS":        config.ADMIN_ROLE_IDS,
        "MANAGER_ROLE_IDS":      config.MANAGER_ROLE_IDS,
        "MEMBER_ROLE_IDS":       config.MEMBER_ROLE_IDS,
        "LOG_UNSUCCESSFUL":      config.LOG_UNSUCCESSFUL,
        "USER_LOG_CHANNEL":      config.LOG_CHANNELS[CommandType.USER],
        "MANAGER_LOG_CHANNEL":   config.LOG_CHANNELS[CommandType.MANAGER],
        "ADMIN_LOG_CHANNEL":     config.LOG_CHANNELS[CommandType.ADMIN],
        "ALL_TABLES":            config.ALL_TABLES,
    }
    with open(SETTINGS_FILE, "w") as f:
        json.dump(data, f, indent=4)
async def verifyCommandPermissions(ctx_or_interaction, command_type: CommandType = None) -> bool:
    if isinstance(ctx_or_interaction, discord.Interaction):
        user             = ctx_or_interaction.user
        guild_permissions = ctx_or_interaction.user.guild_permissions
        if ctx_or_interaction.command is not None:
            command_name = ctx_or_interaction.command.name
        else:
            custom_id = ctx_or_interaction.data.get("custom_id", "unknown") if ctx_or_interaction.data else "unknown"
            command_name = f"component:{custom_id}"
        _client          = ctx_or_interaction.client
    else:
        user             = ctx_or_interaction.author
        guild_permissions = ctx_or_interaction.author.guild_permissions
        command_name     = ctx_or_interaction.command.name
        _client          = ctx_or_interaction.bot

    if command_type is None:
        allowed = True
    else:
        user_role_ids = [role.id for role in user.roles]
        allowed_roles = []
        if command_type == CommandType.USER:
            allowed_roles += config.MEMBER_ROLE_IDS
        if command_type in (CommandType.MANAGER, CommandType.USER):
            allowed_roles += config.MANAGER_ROLE_IDS
        if command_type in (CommandType.ADMIN, CommandType.MANAGER, CommandType.USER):
            allowed_roles += config.ADMIN_ROLE_IDS

        allowed_roles += config.SERVER_ADMIN_ROLE_IDS

        if guild_permissions.administrator:
            allowed = True
        elif any(role_id in allowed_roles for role_id in user_role_ids):
            allowed = True
        else:
            allowed = False

    logging.info(f"[{'Unprotected' if command_type is None else command_type.value}] [{command_name}] {user} - {'Allowed' if allowed else 'Denied'}")

    return allowed



    channel_id = config.LOG_CHANNELS.get(command_type) if command_type is not None else None
    channel = _client.get_channel(channel_id) if isinstance(channel_id, int) and channel_id != 0 else None

    if channel and (allowed or config.LOG_UNSUCCESSFUL):
        embed = discord.Embed(
            title=f"[{command_type.value}] {'Unsuccessful ' if not allowed else ''}Command Log",
            description=(
                f"{user.mention} was denied from executing `{command_name}`"
                if not allowed
                else f"{user.mention} executed `{command_name}`"
            ),
            color={
                CommandType.USER:    discord.Color.light_grey(),
                CommandType.MANAGER: discord.Color.orange(),
                CommandType.ADMIN:   discord.Color.red(),
                CommandType.SERVER_ADMIN:   discord.Color.red(),
            }[command_type],
        )
        embed.add_field(name="Status",    value="Allowed" if allowed else "Denied")
        embed.add_field(name="User ID",   value=f"``{user.id}``")
        embed.add_field(name="Timestamp", value=discord.utils.format_dt(discord.utils.utcnow()))
        embed.set_thumbnail(url={
            CommandType.USER:    "https://cdn.discordapp.com/emojis/1512608514919632896.png",
            CommandType.MANAGER: "https://cdn.discordapp.com/emojis/1512608333394350301.png",
            CommandType.ADMIN:   "https://cdn.discordapp.com/emojis/1512608289819463762.png",
            CommandType.SERVER_ADMIN:   "https://cdn.discordapp.com/emojis/1512608289819463762.png",
        }[command_type])
        await channel.send(embed=embed)

    if not allowed:
        msg = f"{PERMISSON} You don't have permission to use this command."
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.response.send_message(msg)
        else:
            await ctx_or_interaction.send(msg)

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
        self.dynamic_items = []  # track items added per-page

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
        self.current_page = max(0, self.current_page - 1)
        await self.refresh(interaction)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.secondary)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = min(len(self.embeds) - 1, self.current_page + 1)
        await self.refresh(interaction)


class SelectChannels_Menu(discord.ui.Select):
    def __init__(self, channels: list[discord.TextChannel], on_submit):
        self.on_submit = on_submit
        options = [discord.SelectOption(label=c.name, value=str(c.id)) for c in channels[:25]]
        super().__init__(placeholder="Select a channel...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        selected = [interaction.guild.get_channel(int(v)) for v in self.values]
        await self.on_submit(interaction, [c for c in selected if c])


class SelectRoles_Menu(discord.ui.Select):
    def __init__(self, roles, on_submit):
        self.on_submit = on_submit
        options = [discord.SelectOption(label=r.name, value=str(r.id)) for r in roles[:25]]
        super().__init__(placeholder="Select roles...", min_values=1, max_values=len(options), options=options)

    async def callback(self, interaction: discord.Interaction):
        selected = [interaction.guild.get_role(int(v)) for v in self.values]
        await self.on_submit(interaction, [r for r in selected if r])

async def table_name_autocomplete(interaction: discord.Interaction, current: str):
    return [
        app_commands.Choice(name=t["name"], value=t["name"])
        for t in config.ALL_TABLES
        if current.lower() in t["name"].lower()
    ][:25]  