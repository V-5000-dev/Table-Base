import discord
import config
from discord.ext import commands
from discord import app_commands
from config import CHECK, EMPTY_CELL, ERROR, MAX_COLUMNS_NOTE, PERMISSON, X, CommandType
from utils import (
    MAX_MODAL_LABEL_LENGTH, authorize_table, find_row_index, get_request_channel_id, has_table_access,
    is_blank_input, respond, save_settings, table_name_autocomplete, upsert_row
)


def find_pending_request(guild_id: int, message_id: int):
    """Return the (table, request) posted as a message, or None."""
    for table in config.get_guild(guild_id)["ALL_TABLES"]:
        for request in table.get("pending_requests", []):
            if request["message_id"] == message_id:
                return table, request
    return None


def build_request_embed(table: dict, request: dict, status: str = "Pending",
                        color: discord.Color = discord.Color.gold(), reviewer=None) -> discord.Embed:
    old_values = request["old_values"]
    action = "Update" if old_values is not None else "Add"

    embed = discord.Embed(
        title=f"{action} Row Request - {table['name']}",
        description=f"**Status: {status}**",
        color=color
    )
    embed.set_author(name=f"Status: {status}")
    embed.add_field(name="User", value=request["user"], inline=False)
    embed.add_field(name="Timestamp", value=request["timestamp"], inline=False)

    for column, value in request["values"].items():
        if old_values is None or old_values.get(column) != value:
            embed.add_field(name=column, value=value[:1024], inline=False)

    if reviewer is not None:
        embed.add_field(name="Reviewed By", value=reviewer.mention, inline=False)

    return embed


def build_ping_content(table: dict) -> str | None:
    if not table.get("ping_managers", False):
        return None

    manager_role_ids = table.get("manager_role_ids", [])
    if not manager_role_ids:
        return None

    return " ".join(f"<@&{r}>" for r in manager_role_ids)


class AddRequest(discord.ui.View):
    """
    Accept and Reject buttons on a request message.

    The view holds no state. It finds its request from the message, and
    the fixed custom_ids let one registered instance handle every request,
    so requests keep working after a restart.
    """
    def __init__(self):
        super().__init__(timeout=None)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        found = find_pending_request(interaction.guild_id, interaction.message.id)
        if found is None:
            await interaction.response.send_message(
                f"{ERROR} ``This request is no longer active. Its table may have been deleted.``", ephemeral=True
            )
            return False

        table, _ = found
        guild_settings = config.get_guild(interaction.guild_id)
        if not has_table_access(interaction.user, guild_settings, CommandType.MANAGER, table):
            await interaction.response.send_message(
                f"{PERMISSON} ``Only this table's managers can review requests.``", ephemeral=True
            )
            return False

        return True

    async def _close_request(self, interaction: discord.Interaction, table: dict, request: dict,
                             status: str, color: discord.Color):
        table["pending_requests"].remove(request)
        save_settings()

        closed_view = AddRequest()
        for child in closed_view.children:
            child.disabled = True
        closed_view.stop()

        embed = build_request_embed(table, request, status, color, interaction.user)
        await interaction.response.edit_message(embed=embed, view=closed_view)

        try:
            requester = await interaction.client.fetch_user(request["requester_id"])
            await requester.send(
                content=f"Your request for table **{table['name']}** has been **{status}**.",
                embed=embed
            )
        except discord.HTTPException:
            pass

    @discord.ui.button(label="Accept", style=discord.ButtonStyle.grey, emoji=f"{CHECK}", custom_id="table_request:accept")
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        table, request = find_pending_request(interaction.guild_id, interaction.message.id)
        upsert_row(table, request["user"], request["values"], request["timestamp"])
        await self._close_request(interaction, table, request, "Approved", discord.Color.green())

    @discord.ui.button(label="Reject", style=discord.ButtonStyle.gray, emoji=f"{X}", custom_id="table_request:reject")
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        table, request = find_pending_request(interaction.guild_id, interaction.message.id)
        await self._close_request(interaction, table, request, "Rejected", discord.Color.red())


def request_blocker(client, guild_settings: dict, table: dict) -> str | None:
    """Return why a request cannot be made for this table, or None."""
    custom_columns = len(table["column_names"]) - 2

    if custom_columns == 0:
        return f"{ERROR} ``This table has no columns.``"
    if custom_columns > 20:
        return f"{ERROR} ``{MAX_COLUMNS_NOTE}``"
    if client.get_channel(get_request_channel_id(table, guild_settings)) is None:
        return f"{ERROR} ``Could not find the request review channel. Contact an admin.``"
    return None


async def submit_request(client, guild_settings: dict, table: dict, requester, values: dict) -> str | None:
    """Post a request to the table's review channel. Returns an error, or None."""
    index = find_row_index(table, requester.mention)
    old_values = None
    if index is not None:
        old_values = dict(zip(table["column_names"][2:], table["data"][index][2:]))
        if all(old_values.get(column) == value for column, value in values.items()):
            return f"{ERROR} ``No changes were made, request cancelled.``"

    review_channel = client.get_channel(get_request_channel_id(table, guild_settings))
    if review_channel is None:
        return f"{ERROR} ``Could not find the request review channel. Contact an admin.``"

    request = {
        "requester_id": requester.id,
        "user": requester.mention,
        "timestamp": discord.utils.format_dt(discord.utils.utcnow()),
        "values": values,
        "old_values": old_values,
    }

    try:
        message = await review_channel.send(
            content=build_ping_content(table),
            embed=build_request_embed(table, request),
            view=AddRequest(),
            allowed_mentions=discord.AllowedMentions(roles=True)
        )
    except discord.HTTPException:
        return f"{ERROR} ``Could not post to the request review channel. Contact an admin.``"

    request["message_id"] = message.id
    table.setdefault("pending_requests", []).append(request)
    save_settings()
    return None


class ContinueRowInput(discord.ui.View):
    """
    Bridges two modal pages.

    Discord will not let you open a modal directly in response to a
    modal *submission* (MODAL_SUBMIT interactions can only be answered
    with a message-type response). So instead of chaining
    modal -> modal, we chain modal -> message-with-button -> modal:

        1. Page 1 modal submits -> bot sends a message with a
           "Continue" button (a valid response to MODAL_SUBMIT).
        2. User clicks the button -> that's a component interaction,
           which IS allowed to open a modal -> bot opens page 2.
    """
    def __init__(self, table: dict, values: dict, next_page: int):
        super().__init__(timeout=300)
        self.table = table
        self.values = values
        self.next_page = next_page

    @discord.ui.button(label="Continue", style=discord.ButtonStyle.grey, emoji="➡️")
    async def continue_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        next_modal = AddRow_Input(
            self.table, interaction.user.mention, values=self.values, page=self.next_page
        )
        await interaction.response.send_modal(next_modal)

        for child in self.children:
            child.disabled = True
        try:
            await interaction.edit_original_response(view=self)
        except discord.HTTPException:
            pass

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True


class AddRow_Input(discord.ui.Modal, title="Add/Update Row"):
    def __init__(self, table: dict, user_mention: str, values: dict | None = None, page: int = 0):
        columns = table["column_names"][2:]
        self.pages = [columns[i:i + 5] for i in range(0, len(columns), 5)]
        page = min(page, max(len(self.pages) - 1, 0))
        self.page_columns = self.pages[page] if self.pages else []

        page_count = len(self.pages)
        title = "Add/Update Row" if page_count <= 1 else f"Add/Update Row (Page {page + 1}/{page_count})"
        super().__init__(title=title)

        self.table = table
        self.page = page
        self.values = values if values is not None else {}
        self.inputs = []

        index = find_row_index(table, user_mention)
        existing = table["data"][index] if index is not None else None

        start_offset = page * 5
        for i, col in enumerate(self.page_columns):
            default_value = None
            if existing is not None:
                default_value = existing[2 + start_offset + i]
                if default_value == EMPTY_CELL:
                    default_value = None

            text_input = discord.ui.TextInput(
                label=col[:MAX_MODAL_LABEL_LENGTH],
                placeholder="Type here... (leave it blank to keep current value)",
                required=False,
                max_length=200,
                default=default_value
            )
            self.add_item(text_input)
            self.inputs.append(text_input)

    async def on_submit(self, interaction: discord.Interaction):
        for column, text_input in zip(self.page_columns, self.inputs):
            value = text_input.value.strip()
            if is_blank_input(value):
                self.values.pop(column, None)
            else:
                self.values[column] = value

        if self.page + 1 < len(self.pages):
            view = ContinueRowInput(self.table, self.values, self.page + 1)
            await interaction.response.send_message(
                f"Page {self.page + 1}/{len(self.pages)} saved. Click **Continue** to fill out the next page.",
                view=view,
                ephemeral=True
            )
            return

        guild_settings = config.get_guild(interaction.guild_id)
        error = await submit_request(interaction.client, guild_settings, self.table, interaction.user, self.values)
        await interaction.response.send_message(
            error or f"{CHECK} ``Your request has been submitted.``", ephemeral=True
        )


class Add_Row_By_Request(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        self.bot.add_view(AddRequest())

    @app_commands.command(name="add-row-by-request", description="Create a request to add or update your row in the table.")
    @app_commands.autocomplete(name=table_name_autocomplete)
    async def table_add_row_request(self, interaction: discord.Interaction, name: str):
        table = await authorize_table(interaction, name, CommandType.USER)
        if table is None:
            return

        guild_settings = config.get_guild(interaction.guild_id)
        error = request_blocker(interaction.client, guild_settings, table)
        if error:
            await respond(interaction, error)
            return

        await interaction.response.send_modal(AddRow_Input(table, interaction.user.mention))

    @commands.command(name="add-row-by-request")
    async def table_add_row_prefix_request(self, ctx, name: str, *values: str):
        table = await authorize_table(ctx, name, CommandType.USER)
        if table is None:
            return

        guild_settings = config.get_guild(ctx.guild.id)
        error = request_blocker(ctx.bot, guild_settings, table)
        if error:
            await ctx.send(error)
            return

        row_values = {
            column: value
            for column, value in zip(table["column_names"][2:], values)
            if not is_blank_input(value)
        }

        error = await submit_request(ctx.bot, guild_settings, table, ctx.author, row_values)
        await ctx.send(error or f"{CHECK} ``Your request has been submitted.``")


async def setup(bot):
    await bot.add_cog(Add_Row_By_Request(bot))
