import discord
import io
from discord.ext import commands
from discord import app_commands
from config import CommandType
from utils import authorize_table, format_row, respond, send_row_pages, table_name_autocomplete, wants_raw


class View_Table(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def build_table_file(self, table, name):
        """Builds a .txt file representation of the table."""
        columns = table["column_names"]
        rows = table["data"]

        lines = [f"Table: {name}", ""]

        if not columns:
            lines.append("(no columns)")
        elif not rows:
            lines.append(", ".join(columns))
            lines.append("(no rows)")
        else:
            lines.append(" | ".join(str(c) for c in columns))
            lines.append("-" * 40)
            for row_index, row in enumerate(rows, start=1):
                lines.append(f"{row_index}: {' | '.join(str(cell) for cell in row)}")

        content = "\n".join(lines)
        buffer = io.BytesIO(content.encode("utf-8"))
        return discord.File(buffer, filename=f"{name}.txt")

    async def show_table(self, ctx_or_interaction, name: str, view_raw: bool):
        table = await authorize_table(ctx_or_interaction, name, CommandType.MANAGER)
        if table is None:
            return

        if view_raw:
            await respond(ctx_or_interaction, file=self.build_table_file(table, name), ephemeral=False)
            return

        columns = table["column_names"]
        blocks = [
            f"**Row {row_index}**\n{format_row(columns, row)}"
            for row_index, row in enumerate(table["data"], start=1)
        ]
        await send_row_pages(ctx_or_interaction, f"Table: {name}", blocks or ["(no rows)"])

    @app_commands.command(name="view-table", description="View the entire table.")
    @app_commands.autocomplete(name=table_name_autocomplete)
    @app_commands.describe(view_raw="Send the table as a .txt file instead of an embed.")
    async def table_view_all(self, interaction: discord.Interaction, name: str, view_raw: bool = False):
        await self.show_table(interaction, name, view_raw)

    @commands.command(name="view-table")
    async def table_view_all_prefix(self, ctx, name: str, view_raw: str = None):
        await self.show_table(ctx, name, wants_raw(view_raw))


async def setup(bot):
    await bot.add_cog(View_Table(bot))
