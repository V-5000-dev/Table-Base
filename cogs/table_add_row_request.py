import discord
import config
from discord.ext import commands
from discord import app_commands
from config import GUILD_ID, CHECK, ERROR, X, CommandType
from utils import verifyCommandPermissions, save_settings, table_name_autocomplete

class AddRequest(discord.ui.View):
    def __init__(self, table: dict, existing_index: int | None, requester: discord.Member, new_row: list):
        super().__init__(timeout=None)
        self.table = table
        self.existing_index = existing_index
        self.requester = requester
        self.new_row = new_row

    def build_embed(self, status: str = "Pending", color: discord.Color = discord.Color.gold()):
        action = "Update" if self.existing_index is not None else "Add"
        embed = discord.Embed(
            title=f"{action} Row Request - {self.table['name']}",
            color=color
        )
        embed.set_footer(text=f"Status: {status}")

        if self.existing_index is not None:
            old_row = self.table["data"][self.existing_index]
        else:
            old_row = [None] * len(self.new_row)

        for i, (col, old_val, new_val) in enumerate(zip(self.table["column_names"], old_row, self.new_row)):
            if i < 2:
                # User / Timestamp columns - just show the current value
                value = str(new_val)
            else:
                old_display = str(old_val) if old_val is not None else "None"
                value = f"{old_display} → {new_val}"

            embed.add_field(name=col, value=value, inline=False)

        return embed
    @discord.ui.button(label="Accept", style=discord.ButtonStyle.grey, emoji=f"{CHECK}")
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await verifyCommandPermissions(interaction, CommandType.MANAGER):
            return

        # Re-check for an existing row at accept time, in case data changed
        # since the request was submitted
        current_index = next(
            (i for i, r in enumerate(self.table["data"]) if r[0] == self.new_row[0]),
            None
        )

        if current_index is not None:
            existing_row = self.table["data"][current_index]
            final_row = [
                existing_row[i] if val == "null" else val
                for i, val in enumerate(self.new_row)
            ]
            self.table["data"][current_index] = final_row
        else:
            final_row = list(self.new_row)
            self.table["data"].append(final_row)
            self.table["rows"] += 1

        save_settings()

        for child in self.children:
            child.disabled = True

        embed = self.build_embed(status=f"Approved by {interaction.user.mention}", color=discord.Color.green())
        await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(label="Reject", style=discord.ButtonStyle.gray, emoji=f"{X}")
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await verifyCommandPermissions(interaction, CommandType.MANAGER):
            return

        for child in self.children:
            child.disabled = True

        embed = self.build_embed(status=f"Rejected by {interaction.user.mention}", color=discord.Color.red())
        await interaction.response.edit_message(embed=embed, view=self)


class AddRow_Input(discord.ui.Modal, title="Add/Update Row"):
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
        new_row = ["null" for _ in range(self.table["columns"])]
        new_row[0] = interaction.user.mention
        new_row[1] = discord.utils.format_dt(discord.utils.utcnow())

        for i, text_input in enumerate(self.inputs):
            value = text_input.value.strip()

            if value.lower() == "null" or not value:
                if self.existing_index is not None:
                    new_row[2 + i] = self.table["data"][self.existing_index][2 + i]
                else:
                    new_row[2 + i] = "null"
            else:
                new_row[2 + i] = value

        view = AddRequest(self.table, self.existing_index, interaction.user, new_row)
        embed = view.build_embed()

        review_channel = interaction.client.get_channel(config.TABLE_REQUEST_CHANNEL_ID)
        if review_channel is None:
            await interaction.response.send_message(
                f"{ERROR} ``Could not find the request review channel. Contact an admin.``", ephemeral=True
            )
            return

        await review_channel.send(embed=embed, view=view)

        await interaction.response.send_message(
            f"{CHECK} ``Your request has been submitted for review.``", ephemeral=True
        )

class Table_Add_Row_Request(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="table-add-row-request", description="Create a request to add or update your row in the table. ")
    @app_commands.autocomplete(name=table_name_autocomplete)
    async def table_add_row_request(self, interaction: discord.Interaction, name: str):
        if not await verifyCommandPermissions(interaction, CommandType.USER):
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
            (i for i, r in enumerate(table["data"]) if r[0] == interaction.user.mention),
            None
        )

        await interaction.response.send_modal(AddRow_Input(table, existing_index))

    @commands.command(name="table-add-row-request")
    async def table_add_row_prefix_request(self, ctx, name: str, *values: str):
        if not await verifyCommandPermissions(ctx, CommandType.USER):
            return

        table = next((t for t in config.ALL_TABLES if t["name"] == name), None)
        if table is None:
            await ctx.send(f"{ERROR} ``Table``  ``{name}`` ``not found.``")
            return

        new_row = ["None" for _ in range(table["columns"])]
        new_row[0] = ctx.author.mention
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
    await bot.add_cog(Table_Add_Row_Request(bot))