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
                value = str(new_val)
            else:
                if new_val == "None":
                    continue
            old_display = str(old_val) if old_val is not None else "None"
            value = f"{old_display} → {new_val}"

        return embed

    def build_ping_content(self):
        if not self.table.get("ping_managers", False):
            return None

        manager_role_ids = self.table.get("manager_role_ids", [])

        if not manager_role_ids:
            return None

        return " ".join(f"<@&{r}>" for r in manager_role_ids)

    @discord.ui.button(label="Accept", style=discord.ButtonStyle.grey, emoji=f"{CHECK}")
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        current_index = next(
            (i for i, r in enumerate(self.table["data"]) if r[0] == self.new_row[0]),
            None
        )

        if current_index is not None:
            existing_row = self.table["data"][current_index]
            final_row = [
                existing_row[i] if val == "None" else val
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

            text_input = discord.ui.TextInput(
                label=col,
                placeholder="Type here... (leave it blank to keep current value)",
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

            if value.lower() == "None" or not value:
                if self.existing_index is not None:
                    new_row[2 + i] = self.table["data"][self.existing_index][2 + i]
                else:
                    new_row[2 + i] = "None"
            else:
                new_row[2 + i] = value

        view = AddRequest(self.table, self.existing_index, interaction.user, new_row)
        embed = view.build_embed()
        content = view.build_ping_content()

        review_channel = interaction.client.get_channel(config.TABLE_REQUEST_CHANNEL_ID)
        if review_channel is None:
            await interaction.response.send_message(
                f"{ERROR} ``Could not find the request review channel. Contact an admin.``", ephemeral=True
            )
            return

        await review_channel.send(
            content=content,
            embed=embed,
            view=view,
            allowed_mentions=discord.AllowedMentions(roles=True)
        )

        await interaction.response.send_message(
            f"{CHECK} ``Your request has been submitted.``", ephemeral=True
        )


class Table_Add_Row_Request(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="table-add-row-request", description="Create a request to add or update your row in the table.")
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

        if len(table["column_names"]) - 2 == 0:
            await interaction.response.send_message(
                f"{ERROR} ``This table has no columns.``",
                ephemeral=True
            )
            return

        if len(table["column_names"]) - 2 > 20:
            await interaction.response.send_message(
                f"{ERROR} ``This table has too many columns to add a row via this command "
                f"(max 20 supported).``",
                ephemeral=True
            )
            return

        review_channel = interaction.client.get_channel(config.TABLE_REQUEST_CHANNEL_ID)
        if review_channel is None:
            await interaction.response.send_message(
                f"{ERROR} ``Could not find the request review channel. Contact an admin.``", ephemeral=True
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
            await ctx.send(f"{ERROR} ``Table`` ``{name}`` ``not found.``")
            return

        if len(table["column_names"]) - 2 == 0:
            await ctx.send(f"{ERROR} ``This table has no columns.``")
            return

        if len(table["column_names"]) - 2 > 20:
            await ctx.send(
                f"{ERROR} ``This table has too many columns to add a row via this command "
                f"(max 20 supported).``"
            )
            return

        review_channel = ctx.bot.get_channel(config.TABLE_REQUEST_CHANNEL_ID)
        if review_channel is None:
            await ctx.send(f"{ERROR} ``Could not find the request review channel. Contact an admin.``")
            return

        existing_index = next(
            (i for i, r in enumerate(table["data"]) if r[0] == ctx.author.mention),
            None
        )

        new_row = ["None" for _ in range(table["columns"])]
        new_row[0] = ctx.author.mention
        new_row[1] = discord.utils.format_dt(discord.utils.utcnow())

        custom_columns = table["column_names"][2:]
        for i in range(len(custom_columns)):
            value = values[i] if i < len(values) else "None"

            if value.lower() == "None":
                if existing_index is not None:
                    new_row[2 + i] = table["data"][existing_index][2 + i]
                else:
                    new_row[2 + i] = "None"
            else:
                new_row[2 + i] = value

        view = AddRequest(table, existing_index, ctx.author, new_row)
        embed = view.build_embed()
        content = view.build_ping_content()

        await review_channel.send(
            content=content,
            embed=embed,
            view=view,
            allowed_mentions=discord.AllowedMentions(roles=True)
        )

        await ctx.send(f"{CHECK} ``Your request has been submitted.``")


async def setup(bot):
    await bot.add_cog(Table_Add_Row_Request(bot))