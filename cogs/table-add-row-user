import discord
import config
from discord.ext import commands
from discord import app_commands
from config import GUILD_ID, CHECK, ERROR, CommandType
from utils import verifyCommandPermissions, save_settings, table_name_autocomplete


class AddRow_Input(discord.ui.Modal, title="Add/Update Row of any user."):
    def __init__(self, table: dict, existing_index: int | None):
        super().__init__()
        self.table = table
        self.existing_index = existing_index
        self.field_columns = table["column_names"][2:]  
        self.inputs = []

        for i, col in enumerate(self.field_columns):
            default_value = None
            if existing_index is not None:
                default_value = table["data"][existing_index][2 + i]
                if default_value == "null":
                    default_value = None

            text_input = discord.ui.TextInput(
                label=col,
                placeholder="Type here... (\"null\" keeps current value)",
                required=False,
                max_length=200,
                default=default_value
            )
            self.add_item(text_input)
            self.inputs.append(text_input)

    async def on_submit(self, interaction: discord.Interaction):
        new_row = ["None" for _ in range(self.table["columns"])]
        new_row[0] = interaction.user.mention
        new_row[1] = discord.utils.format_dt(discord.utils.utcnow())

        for i, text_input in enumerate(self.inputs):
            value = text_input.value.strip()

            if value.lower() == "none" or not value:
                if self.existing_index is not None:
                    new_row[2 + i] = self.table["data"][self.existing_index][2 + i]
                else:
                    new_row[2 + i] = "None"
            else:
                new_row[2 + i] = value

        if self.existing_index is not None:
            self.table["data"][self.existing_index] = new_row
            save_settings()
            await interaction.response.send_message(
                f"{CHECK} ``{self.user} row in table`` ``{self.table['name']}`` ``has been updated.``", ephemeral=True
            )
        else:
            self.table["data"].append(new_row)
            self.table["rows"] += 1
            save_settings()
            await interaction.response.send_message(
                f"{CHECK} ``Row added to table`` ``{self.table['name']}``", ephemeral=True
            )


class Table_Add_Row_User(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="table-add-row-user", description="Add or update your row in the table.")
    @app_commands.autocomplete(name=table_name_autocomplete)
    async def table_add_row(self, interaction: discord.Interaction, name: str, user: str):
        if not await verifyCommandPermissions(interaction, CommandType.ADMIN):
            return

        table = next((t for t in config.ALL_TABLES if t["name"] == name), None)
        if table is None:
            await interaction.response.send_message(
                f"{ERROR} ``Table`` ``{name}`` ``not found.``", ephemeral=True
            )
            return

        if len(table["column_names"]) - 2 > 20:
            await interaction.response.send_message(
                f"{ERROR} ``This table has too many custom columns to add a row via this command "
                f"(max 20 supported).``",
                ephemeral=True
            )
            return

        existing_index = next(
            (i for i, r in enumerate(table["data"]) if r[0] == user),
            None
        )

        await interaction.response.send_modal(AddRow_Input(table, existing_index))

    @commands.command(name="table-add-row-user")
    async def table_add_row_prefix(self, ctx, name: str, user: str, *values: str):
        if not await verifyCommandPermissions(ctx, CommandType.MANAGER):
            return

        table = next((t for t in config.ALL_TABLES if t["name"] == name), None)
        if table is None:
            await ctx.send(f"{ERROR} ``Table``  ``{name}`` ``not found.``")
            return

        new_row = ["None" for _ in range(table["columns"])]
        new_row[0] = user
        new_row[1] = discord.utils.format_dt(discord.utils.utcnow())

        existing_index = next(
            (i for i, r in enumerate(table["data"]) if r[0] == ctx.author.mention),
            None
        )

        custom_columns = table["column_names"][2:]
        for i in range(len(custom_columns)):
            value = values[i] if i < len(values) else "None"

            if value.lower() == "none":
                if existing_index is not None:
                    new_row[2 + i] = table["data"][existing_index][2 + i]
                else:
                    new_row[2 + i] = "None"
            else:
                new_row[2 + i] = value

        if existing_index is not None:
            table["data"][existing_index] = new_row
            save_settings()
            await ctx.send(f"{CHECK} ``Your row in table`` ``{name}`` ``has been updated.``")
        else:
            table["data"].append(new_row)
            table["rows"] += 1
            save_settings()
            await ctx.send(f"{CHECK} ``Row added to table`` ``{name}``")


async def setup(bot):
    await bot.add_cog(Table_Add_Row_User(bot))