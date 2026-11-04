import discord
import io
from discord.ext import commands
from discord import app_commands
from config import ERROR, CommandType
from utils import authorize_table, format_row, respond, send_row_pages, table_name_autocomplete, wants_raw


class View_Row_By_ID(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def build_row_file(self, table, name, row_number, row):
        columns = table["column_names"]
        lines = [f"Table: {name} | Row {row_number}", ""]
        lines.append(" | ".join(str(c) for c in columns))
        lines.append("-" * 40)
        lines.append(" | ".join(str(cell) for cell in row))
        content = "\n".join(lines)
        buffer = io.BytesIO(content.encode("utf-8"))
        return discord.File(buffer, filename=f"{name}_row_{row_number}.txt")

    async def show_row(self, ctx_or_interaction, name: str, row_number: int, view_raw: bool):
        table = await authorize_table(ctx_or_interaction, name, CommandType.MANAGER)
        if table is None:
            return

        if not table["data"]:
            await respond(ctx_or_interaction, f"{ERROR} ``Table`` ``{name}`` ``has no rows.``")
            return

        if row_number < 1 or row_number > len(table["data"]):
            await respond(ctx_or_interaction, f"{ERROR} ``Row number must be between 1 and {len(table['data'])}.``")
            return

        row = table["data"][row_number - 1]

        if view_raw:
            await respond(ctx_or_interaction, file=self.build_row_file(table, name, row_number, row), ephemeral=False)
            return

        await send_row_pages(
            ctx_or_interaction, f"Table: {name} | Row {row_number}", [format_row(table["column_names"], row)]
        )

    @app_commands.command(name="view-row-by-id", description="View a row in the table by row number.")
    @app_commands.autocomplete(name=table_name_autocomplete)
    @app_commands.describe(row="The row number (starting at 1).", view_raw="Send the row as a .txt file instead of an embed.")
    async def table_view_row_by_id(self, interaction: discord.Interaction, name: str, row: int, view_raw: bool = False):
        await self.show_row(interaction, name, row, view_raw)

    @commands.command(name="view-row-by-id")
    async def table_view_row_by_id_prefix(self, ctx, name: str, row: int, view_raw: str = None):
        await self.show_row(ctx, name, row, wants_raw(view_raw))


async def setup(bot):
    await bot.add_cog(View_Row_By_ID(bot))
