import discord
import config
from discord.ext import commands
from discord import app_commands
from config import CHECK, EMPTY_CELL, ERROR, MAX_COLUMNS_NOTE, CommandType
from utils import (
    MAX_MODAL_LABEL_LENGTH, authorize_table, find_row_index, is_blank_input, respond,
    save_settings, table_name_autocomplete, upsert_row
)


def add_row_blocker(table: dict) -> str | None:
    """Return why rows cannot be added to this table, or None."""
    custom_columns = len(table["column_names"]) - 2

    if custom_columns == 0:
        return f"{ERROR} ``This table has no columns.``"
    if custom_columns > 20:
        return f"{ERROR} ``{MAX_COLUMNS_NOTE}``"
    return None


def save_row(table: dict, user: discord.Member, values: dict) -> str:
    """Add or update a user's row and return the confirmation message."""
    updated = upsert_row(table, user.mention, values)
    save_settings()

    if updated:
        return f"{CHECK} {user.mention} ``row in table`` ``{table['name']}`` ``has been updated.``"
    return f"{CHECK} ``Row added to table`` ``{table['name']}`` ``for`` {user.mention}"


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
    def __init__(self, table: dict, target_user: discord.Member, values: dict, next_page: int):
        super().__init__(timeout=300)
        self.table = table
        self.target_user = target_user
        self.values = values
        self.next_page = next_page

    @discord.ui.button(label="Continue", style=discord.ButtonStyle.grey, emoji="➡️")
    async def continue_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        next_modal = AddRow_Input(self.table, self.target_user, values=self.values, page=self.next_page)
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
    def __init__(self, table: dict, target_user: discord.Member, values: dict | None = None, page: int = 0):
        columns = table["column_names"][2:]
        self.pages = [columns[i:i + 5] for i in range(0, len(columns), 5)]
        page = min(page, max(len(self.pages) - 1, 0))
        self.page_columns = self.pages[page] if self.pages else []

        page_count = len(self.pages)
        title = "Add/Update Row" if page_count <= 1 else f"Add/Update Row (Page {page + 1}/{page_count})"
        super().__init__(title=title)

        self.table = table
        self.target_user = target_user
        self.page = page
        self.values = values if values is not None else {}
        self.inputs = []

        index = find_row_index(table, target_user.mention)
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
            view = ContinueRowInput(self.table, self.target_user, self.values, self.page + 1)
            await interaction.response.send_message(
                f"Page {self.page + 1}/{len(self.pages)} saved. Click **Continue** to fill out the next page.",
                view=view,
                ephemeral=True
            )
            return

        await interaction.response.send_message(save_row(self.table, self.target_user, self.values), ephemeral=True)


class Add_Row_By_User(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="add-row-by-user", description="Add or update a user's row in the table.")
    @app_commands.autocomplete(name=table_name_autocomplete)
    async def table_add_row_user(self, interaction: discord.Interaction, name: str, user: discord.Member):
        table = await authorize_table(interaction, name, CommandType.ADMIN)
        if table is None:
            return

        error = add_row_blocker(table)
        if error:
            await respond(interaction, error)
            return

        await interaction.response.send_modal(AddRow_Input(table, user))

        if len(table["column_names"]) - 2 > 5:
            prefix = config.get_guild(interaction.guild_id)["COMMAND_PREFIX"]
            await interaction.followup.send(
                f"``This table has more than 5 columns, so you'll fill out multiple popups in "
                f"sequence — click Continue between each one.``\n"
                f"``Alternatively, the prefix command lets you do it in one step:`` "
                f"``{prefix}add-row-by-user {name} @user value1 value2 ...``",
                ephemeral=True
            )

    @commands.command(name="add-row-by-user")
    async def table_add_row_prefix(self, ctx, name: str, user: discord.Member, *values: str):
        table = await authorize_table(ctx, name, CommandType.ADMIN)
        if table is None:
            return

        error = add_row_blocker(table)
        if error:
            await ctx.send(error)
            return

        row_values = {
            column: value
            for column, value in zip(table["column_names"][2:], values)
            if not is_blank_input(value)
        }
        await ctx.send(save_row(table, user, row_values))


async def setup(bot):
    await bot.add_cog(Add_Row_By_User(bot))
