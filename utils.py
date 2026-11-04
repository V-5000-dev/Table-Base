import asyncio
import discord
import logging
import json
import os
import shutil
import time
import config
from config import CommandType, DEFAULT_PREFIX, EMPTY_CELL, ERROR, PERMISSON
from discord import app_commands

SETTINGS_FILE = "settings.json"

# Earlier versions stored empty cells as these values instead of EMPTY_CELL.
LEGACY_EMPTY_CELLS = ("null", "")

MAX_TABLE_NAME_LENGTH = 50
MAX_MODAL_LABEL_LENGTH = 45

# Embed descriptions allow 4096 characters. This leaves room for a short intro.
EMBED_TEXT_LIMIT = 3900
ROWS_PER_PAGE = 10

# Keeps a reference so that background log posts are not garbage collected.
_log_tasks = set()


def normalize_table(table: dict):
    """Give every row one empty-cell value and the same width as the columns."""
    width = len(table.get("column_names", []))
    for row in table.get("data", []):
        for i, cell in enumerate(row):
            if cell in LEGACY_EMPTY_CELLS:
                row[i] = EMPTY_CELL
        row.extend([EMPTY_CELL] * (width - len(row)))


def apply_guild_data(settings: dict, data: dict):
    """Copy saved guild data into live settings. Used by load and restore."""
    # Backups made before serialize_guild() nest the log channels by enum name.
    legacy_logs = data.get("LOG_CHANNELS") or {}

    settings["TABLE_REQUEST_CHANNEL_ID"] = data.get("TABLE_REQUEST_CHANNEL_ID", 0)
    settings["TABLE_BACKUP_CHANNEL_ID"]  = data.get("TABLE_BACKUP_CHANNEL_ID", 0)
    settings["SERVER_ADMIN_ROLE_IDS"]    = data.get("SERVER_ADMIN_ROLE_IDS", [])
    settings["LOG_UNSUCCESSFUL"]         = data.get("LOG_UNSUCCESSFUL", True)
    settings["LOG_CHANNELS"][CommandType.USER]    = data.get("USER_LOG_CHANNEL", legacy_logs.get("USER", 0))
    settings["LOG_CHANNELS"][CommandType.MANAGER] = data.get("MANAGER_LOG_CHANNEL", legacy_logs.get("MANAGER", 0))
    settings["LOG_CHANNELS"][CommandType.ADMIN]   = data.get("ADMIN_LOG_CHANNEL", legacy_logs.get("ADMIN", 0))
    settings["ALL_TABLES"]               = data.get("ALL_TABLES", [])
    settings["COMMAND_PREFIX"]           = data.get("COMMAND_PREFIX", DEFAULT_PREFIX)
    settings["KEY_EXPIRIES"]             = data.get("KEY_EXPIRIES", {})

    for table in settings["ALL_TABLES"]:
        normalize_table(table)


def serialize_guild(settings: dict) -> dict:
    """Return the JSON form of a guild. Used by save and backup."""
    return {
        "TABLE_REQUEST_CHANNEL_ID": settings["TABLE_REQUEST_CHANNEL_ID"],
        "TABLE_BACKUP_CHANNEL_ID":  settings.get("TABLE_BACKUP_CHANNEL_ID", 0),
        "SERVER_ADMIN_ROLE_IDS":    settings["SERVER_ADMIN_ROLE_IDS"],
        "LOG_UNSUCCESSFUL":         settings["LOG_UNSUCCESSFUL"],
        "USER_LOG_CHANNEL":         settings["LOG_CHANNELS"][CommandType.USER],
        "MANAGER_LOG_CHANNEL":      settings["LOG_CHANNELS"][CommandType.MANAGER],
        "ADMIN_LOG_CHANNEL":        settings["LOG_CHANNELS"][CommandType.ADMIN],
        "ALL_TABLES":               settings["ALL_TABLES"],
        "COMMAND_PREFIX":           settings["COMMAND_PREFIX"],
        "KEY_EXPIRIES":             settings.get("KEY_EXPIRIES", {}),
    }


def _read_settings_file() -> dict:
    """Read the settings file, keeping a copy of it if it cannot be parsed."""
    try:
        with open(SETTINGS_FILE, "r") as f:
            data = json.load(f)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        copy_path = f"{SETTINGS_FILE}.corrupt-{int(time.time())}"
        shutil.copy2(SETTINGS_FILE, copy_path)
        logging.exception(f"{SETTINGS_FILE} is not valid JSON. Kept a copy at {copy_path}")
        return {}
    return data if isinstance(data, dict) else {}


def load_settings():
    """Load all guilds from JSON into memory."""
    for guild_id_str, guild_data in _read_settings_file().items():
        try:
            guild_id = int(guild_id_str)
        except (ValueError, TypeError):
            continue
        if not isinstance(guild_data, dict):
            continue

        apply_guild_data(config.get_guild(guild_id), guild_data)


def save_settings():
    """Save all guilds' settings to JSON."""
    data = _read_settings_file()

    for guild_id, settings in config.GUILD_SETTINGS.items():
        data[str(guild_id)] = serialize_guild(settings)

    # A crash during this write must not damage the existing file.
    temp_path = f"{SETTINGS_FILE}.tmp"
    with open(temp_path, "w") as f:
        json.dump(data, f, indent=4)
        f.flush()
        os.fsync(f.fileno())
    os.replace(temp_path, SETTINGS_FILE)


def find_table(guild_id: int, name: str) -> dict | None:
    return next((t for t in config.get_guild(guild_id)["ALL_TABLES"] if t["name"] == name), None)


def find_row_index(table: dict, mention: str) -> int | None:
    return next((i for i, r in enumerate(table["data"]) if r[0] == mention), None)


def get_request_channel_id(table: dict, guild_settings: dict) -> int:
    """A table's own request channel, or the older server-wide one."""
    return table.get("request_channel_id") or guild_settings["TABLE_REQUEST_CHANNEL_ID"]


def table_name_error(name: str) -> str | None:
    """Return why a table name is not valid, or None if it is valid."""
    if not name:
        return "Table names cannot be empty."
    if len(name) > MAX_TABLE_NAME_LENGTH:
        return f"Table names cannot be longer than {MAX_TABLE_NAME_LENGTH} characters."
    return None


def is_blank_input(value: str) -> bool:
    """True if submitted text means "keep the current value"."""
    return not value or value.lower() in ("none", "null")


def wants_raw(view_raw: str | None) -> bool:
    """True if a prefix command's view_raw argument asks for a file."""
    return bool(view_raw) and view_raw.lower() in ("file", "txt", "true")


def build_row(table: dict, mention: str, timestamp: str, values: dict, existing: list | None = None) -> list:
    """
    Build a row for the table's current columns.

    values maps column names to new text. Columns not in values keep their
    existing cell, so a row stays aligned if columns changed since values
    were collected.
    """
    row = [mention, timestamp]
    for i, column in enumerate(table["column_names"][2:], start=2):
        if column in values:
            row.append(values[column])
        elif existing is not None and i < len(existing):
            row.append(existing[i])
        else:
            row.append(EMPTY_CELL)
    return row


def upsert_row(table: dict, mention: str, values: dict, timestamp: str | None = None) -> bool:
    """Add or update a user's row, and return True if it already existed."""
    timestamp = timestamp or discord.utils.format_dt(discord.utils.utcnow())
    index = find_row_index(table, mention)
    if index is None:
        table["data"].append(build_row(table, mention, timestamp, values))
        table["rows"] += 1
        return False

    table["data"][index] = build_row(table, mention, timestamp, values, table["data"][index])
    return True


async def respond(ctx_or_interaction, content=None, *, ephemeral: bool = True, **kwargs):
    """Reply to a command. ephemeral only applies to slash commands."""
    if isinstance(ctx_or_interaction, discord.Interaction):
        await ctx_or_interaction.response.send_message(content, ephemeral=ephemeral, **kwargs)
    else:
        await ctx_or_interaction.send(content, **kwargs)


def has_table_access(member: discord.Member, guild_settings: dict, command_type: CommandType, table: dict | None = None) -> bool:
    """
    Check a member's access to a command type.

    Given a table, only that table's roles count. Without one, a role on any
    table counts.
    """
    if member.guild_permissions.administrator:
        return True

    role_ids = [role.id for role in member.roles]

    if any(r in guild_settings["SERVER_ADMIN_ROLE_IDS"] for r in role_ids):
        return True
    if command_type == CommandType.SERVER_ADMIN:
        return False

    allowed_keys = {
        CommandType.USER:    ("member_role_ids", "manager_role_ids", "admin_role_ids"),
        CommandType.MANAGER: ("manager_role_ids", "admin_role_ids"),
        CommandType.ADMIN:   ("admin_role_ids",),
    }[command_type]

    tables = [table] if table is not None else guild_settings["ALL_TABLES"]
    return any(
        r in t.get(key, [])
        for t in tables
        for key in allowed_keys
        for r in role_ids
    )


async def _post_command_log(channel, embed: discord.Embed):
    try:
        await channel.send(embed=embed)
    except discord.HTTPException:
        logging.exception(f"Could not post a command log to channel {channel.id}")


async def verifyCommandPermissions(ctx_or_interaction, command_type: CommandType, table: dict | None = None) -> bool:
    if isinstance(ctx_or_interaction, discord.Interaction):
        user = ctx_or_interaction.user
        client = ctx_or_interaction.client
        guild_id = ctx_or_interaction.guild_id
    else:
        user = ctx_or_interaction.author
        client = ctx_or_interaction.bot
        guild_id = ctx_or_interaction.guild.id if ctx_or_interaction.guild else None

    if guild_id is None:
        await respond(ctx_or_interaction, f"{ERROR} ``This command can only be used in a server.``")
        return False

    command_name = ctx_or_interaction.command.name
    guild_settings = config.get_guild(guild_id)
    allowed = has_table_access(user, guild_settings, command_type, table)

    should_log = allowed or guild_settings["LOG_UNSUCCESSFUL"]

    if should_log:
        logging.info(
            f"[{command_type.value}] [{command_name}] {user} "
            f"- {'Allowed' if allowed else 'Denied'}"
        )

        # Server admin commands share the Admin log channel.
        log_type = CommandType.ADMIN if command_type == CommandType.SERVER_ADMIN else command_type
        channel = client.get_channel(guild_settings["LOG_CHANNELS"].get(log_type, 0))
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

            # Runs in the background so that it cannot fail or delay the command.
            task = asyncio.create_task(_post_command_log(channel, embed))
            _log_tasks.add(task)
            task.add_done_callback(_log_tasks.discard)

    if not allowed:
        await respond(ctx_or_interaction, f"{PERMISSON} You don't have permission to use this command.")

    return allowed


async def authorize_table(ctx_or_interaction, name: str, command_type: CommandType) -> dict | None:
    """
    Find a table and check the user's access to it.

    Returns the table, or None after telling the user why not.
    """
    if isinstance(ctx_or_interaction, discord.Interaction):
        guild_id = ctx_or_interaction.guild_id
    else:
        guild_id = ctx_or_interaction.guild.id if ctx_or_interaction.guild else None

    table = find_table(guild_id, name) if guild_id is not None else None

    if not await verifyCommandPermissions(ctx_or_interaction, command_type, table):
        return None

    if table is None:
        await respond(ctx_or_interaction, f"{ERROR} ``Table`` ``{name}`` ``not found.``")

    return table


class PageView(discord.ui.View):
    def __init__(self, embeds, ctx_or_interaction, page_menus=None):
        super().__init__(timeout=300)
        self.embeds = embeds
        self.current_page = 0
        self.message = None
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

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        if self.message is not None:
            try:
                await self.message.edit(view=self)
            except discord.HTTPException:
                pass

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


async def send_page_view(ctx_or_interaction, view: PageView, ephemeral: bool = False):
    """Send a PageView and keep its message so that it can expire cleanly."""
    if isinstance(ctx_or_interaction, discord.Interaction):
        await ctx_or_interaction.response.send_message(embed=view.embeds[0], view=view, ephemeral=ephemeral)
        view.message = await ctx_or_interaction.original_response()
    else:
        view.message = await ctx_or_interaction.send(embed=view.embeds[0], view=view)


def format_row(columns: list, row: list) -> str:
    return "\n".join(f"`{col}`: {cell}" for col, cell in zip(columns, row))


def _split_block(block: str, limit: int) -> list:
    """Split text that is too long for one page, between lines if possible."""
    if len(block) <= limit:
        return [block]

    pieces = []
    current = ""
    for line in block.split("\n"):
        line = line[:limit]
        if current and len(current) + len(line) + 1 > limit:
            pieces.append(current)
            current = ""
        current = f"{current}\n{line}" if current else line
    pieces.append(current)
    return pieces


def paginate_blocks(blocks: list, limit: int = EMBED_TEXT_LIMIT, per_page: int = ROWS_PER_PAGE) -> list:
    """Pack text blocks into pages that fit in an embed description."""
    pages = []
    current = []
    size = 0

    for block in blocks:
        for piece in _split_block(block, limit):
            if current and (size + len(piece) + 2 > limit or len(current) >= per_page):
                pages.append("\n\n".join(current))
                current = []
                size = 0
            current.append(piece)
            size += len(piece) + 2

    if current:
        pages.append("\n\n".join(current))
    return pages


async def send_row_pages(ctx_or_interaction, title: str, blocks: list, intro: str = "", ephemeral: bool = False):
    """Show formatted rows in one embed, or across pages if they do not fit."""
    embeds = [
        discord.Embed(title=title, description=f"{intro}\n\n{page}" if intro else page)
        for page in paginate_blocks(blocks)
    ]

    if len(embeds) == 1:
        await respond(ctx_or_interaction, embed=embeds[0], ephemeral=ephemeral)
    else:
        await send_page_view(
            ctx_or_interaction,
            PageView(embeds=embeds, ctx_or_interaction=ctx_or_interaction),
            ephemeral=ephemeral
        )


class SelectChannels_Menu(discord.ui.ChannelSelect):
    def __init__(self, callback_func, ctx_or_interaction, current_id: int = 0):
        # Showing the current channel is what lets a user deselect and clear it.
        current = ctx_or_interaction.guild.get_channel(current_id) if current_id else None
        super().__init__(
            placeholder="Select a channel...",
            min_values=0,
            max_values=1,
            channel_types=[discord.ChannelType.text],
            default_values=[current] if isinstance(current, discord.TextChannel) else []
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
    def __init__(self, on_submit, ctx_or_interaction, current_ids: list = ()):
        # Showing the current roles is what lets a user deselect and clear them.
        guild = ctx_or_interaction.guild
        current = [role for role in map(guild.get_role, current_ids) if role is not None]
        super().__init__(
            placeholder="Select roles...",
            min_values=0,
            max_values=25,
            default_values=current[:25]
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
    if interaction.guild_id is None:
        return []

    guild_settings = config.get_guild(interaction.guild_id)
    return [
        app_commands.Choice(name=t["name"], value=t["name"])
        for t in guild_settings["ALL_TABLES"]
        if current.lower() in t["name"].lower() and len(t["name"]) <= 100
    ][:25]