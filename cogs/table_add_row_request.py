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
            description=f"**Status: {status}**",
            color=color
        )

        embed.set_author(name=f"Status: {status}")

        old_row = (
            self.table["data"][self.existing_index]
            if self.existing_index is not None
            else [None] * len(self.new_row)
        )

        for col, old_val, new_val in zip(self.table["column_names"], old_row, self.new_row):

       
            if new_val == "None":
                new_val = None

            if new_val == old_val:
                continue

            value = str(new_val) if new_val is not None else "None"

            embed.add_field(name=col, value=value, inline=False)

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
            self.table["data"].append(list(self.new_row))
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
    def __init__(self, table: dict, existing_index: int | None, new_row: list, next_page: int, guild_id: int):
        super().__init__(timeout=300)
        self.table = table
        self.existing_index = existing_index
        self.new_row = new_row
        self.next_page = next_page
        self.guild_id = guild_id

    @discord.ui.button(label="Continue", style=discord.ButtonStyle.grey, emoji="➡️")
    async def continue_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        next_modal = AddRow_Input(
            self.table, self.existing_index,
            new_row=self.new_row, page=self.next_page, guild_id=self.guild_id
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
    def __init__(self, table: dict, existing_index: int | None,
                 new_row: list | None = None, page: int = 0, guild_id: int = 0):
        self.field_columns = table["column_names"][2:]
        self.pages = [self.field_columns[i:i + 5] for i in range(0, len(self.field_columns), 5)]
        page_columns = self.pages[page] if self.pages else []

        page_count = len(self.pages)
        title = "Add/Update Row" if page_count <= 1 else f"Add/Update Row (Page {page + 1}/{page_count})"
        super().__init__(title=title)

        self.table = table
        self.existing_index = existing_index
        self.page = page
        self.guild_id = guild_id
        self.new_row = new_row if new_row is not None else ["None" for _ in range(table["columns"])]
        self.inputs = []

        start_offset = page * 5
        for i, col in enumerate(page_columns):
            col_index = start_offset + i
            default_value = None
            if existing_index is not None:
                default_value = table["data"][existing_index][2 + col_index]
                if default_value == "None":
                    default_value = None

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
        self.new_row[0] = interaction.user.mention
        self.new_row[1] = discord.utils.format_dt(discord.utils.utcnow())

        start_offset = self.page * 5
        for i, text_input in enumerate(self.inputs):
            col_index = start_offset + i
            value = text_input.value.strip()

            if value.lower() == "none" or not value:
                if self.existing_index is not None:
                    self.new_row[2 + col_index] = self.table["data"][self.existing_index][2 + col_index]
                else:
                    self.new_row[2 + col_index] = "None"
            else:
                self.new_row[2 + col_index] = value

        if self.page + 1 < len(self.pages):
            view = ContinueRowInput(self.table, self.existing_index, self.new_row, self.page + 1, self.guild_id)
            await interaction.response.send_message(
                f"Page {self.page + 1}/{len(self.pages)} saved. Click **Continue** to fill out the next page.",
                view=view,
                ephemeral=True
            )
            return

        await self.finalize(interaction)

    async def finalize(self, interaction: discord.Interaction):
        if self.existing_index is not None:
            existing_row = self.table["data"][self.existing_index]
            if self.new_row[2:] == existing_row[2:]:
                await interaction.response.send_message(
                    f"{ERROR} ``No changes were made, request cancelled.``", ephemeral=True
                )
                return

        guild_settings = config.get_guild(self.guild_id)

        view = AddRequest(self.table, self.existing_index, interaction.user, self.new_row)
        embed = view.build_embed()
        content = view.build_ping_content()

        review_channel = interaction.client.get_channel(guild_settings["TABLE_REQUEST_CHANNEL_ID"])
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

        guild_settings = config.get_guild(interaction.guild.id)

        table = next((t for t in guild_settings["ALL_TABLES"] if t["name"] == name), None)
        if table is None:
            await interaction.response.send_message(
                f"{ERROR} ``Table`` ``{name}`` ``not found.``", ephemeral=True
            )
            return

        if len(table["column_names"]) - 2 == 0:
            await interaction.response.send_message(
                f"{ERROR} ``This table has no columns.``", ephemeral=True
            )
            return

        if len(table["column_names"]) - 2 > 20:
            await interaction.response.send_message(
                f"{ERROR} ``This table has too many columns to add a row via this command (max 20 supported).``",
                ephemeral=True
            )
            return

        review_channel = interaction.client.get_channel(guild_settings["TABLE_REQUEST_CHANNEL_ID"])
        if review_channel is None:
            await interaction.response.send_message(
                f"{ERROR} ``Could not find the request review channel. Contact an admin.``", ephemeral=True
            )
            return

        existing_index = next(
            (i for i, r in enumerate(table["data"]) if r[0] == interaction.user.mention),
            None
        )

        await interaction.response.send_modal(AddRow_Input(table, existing_index, guild_id=interaction.guild.id))

    @commands.command(name="table-add-row-request")
    async def table_add_row_prefix_request(self, ctx, name: str, *values: str):
        if not await verifyCommandPermissions(ctx, CommandType.USER):
            return

        guild_settings = config.get_guild(ctx.guild.id)

        table = next((t for t in guild_settings["ALL_TABLES"] if t["name"] == name), None)
        if table is None:
            await ctx.send(f"{ERROR} ``Table`` ``{name}`` ``not found.``")
            return

        if len(table["column_names"]) - 2 == 0:
            await ctx.send(f"{ERROR} ``This table has no columns.``")
            return

        if len(table["column_names"]) - 2 > 20:
            await ctx.send(
                f"{ERROR} ``This table has too many columns to add a row via this command (max 20 supported).``"
            )
            return

        review_channel = ctx.bot.get_channel(guild_settings["TABLE_REQUEST_CHANNEL_ID"])
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

        for i, col in enumerate(table["column_names"][2:]):
            value = values[i] if i < len(values) else "None"
            if value.lower() == "none":
                new_row[2 + i] = table["data"][existing_index][2 + i] if existing_index is not None else "None"
            else:
                new_row[2 + i] = value

        if existing_index is not None and new_row[2:] == table["data"][existing_index][2:]:
            await ctx.send(f"{ERROR} ``No changes were made, request cancelled.``")
            return

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