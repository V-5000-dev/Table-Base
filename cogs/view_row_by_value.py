import discord
import io
from discord.ext import commands
from discord import app_commands
from config import ERROR, CommandType
from utils import authorize_table, format_row, respond, send_row_pages, table_name_autocomplete, wants_raw


class View_Row_By_Value(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def build_rows_file(self, table, name, rows):
        columns = table["column_names"]
        lines = [f"Table: {name}", f"Matched {len(rows)} row(s)", ""]
        lines.append(" | ".join(str(c) for c in columns))
        lines.append("-" * 40)
        for row in rows:
            lines.append(" | ".join(str(cell) for cell in row))
        content = "\n".join(lines)
        buffer = io.BytesIO(content.encode("utf-8"))
        return discord.File(buffer, filename=f"{name}_search.txt")

    async def search_rows(self, ctx_or_interaction, name: str, query: str, view_raw: bool):
        table = await authorize_table(ctx_or_interaction, name, CommandType.MANAGER)
        if table is None:
            return

        matches = [
            (i + 1, row)
            for i, row in enumerate(table["data"])
            if any(query.lower() in str(cell).lower() for cell in row)
        ]
        if not matches:
            await respond(ctx_or_interaction, f"{ERROR} ``No rows found containing`` ``{query}``.")
            return

        if view_raw:
            await respond(
                ctx_or_interaction, file=self.build_rows_file(table, name, [r for _, r in matches]), ephemeral=False
            )
            return

        columns = table["column_names"]
        await send_row_pages(
            ctx_or_interaction,
            f"Table: {name}",
            [f"**Row {row_num}**\n{format_row(columns, row)}" for row_num, row in matches],
            intro=f"Found {len(matches)} matching row(s)"
        )

    @app_commands.command(name="view-row-by-value", description="Search for a value across all rows in a table.")
    @app_commands.autocomplete(name=table_name_autocomplete)
    @app_commands.describe(
        query="The value to search for.",
        view_raw="Send results as a .txt file instead of an embed."
    )
    async def table_view_data(self, interaction: discord.Interaction, name: str, query: str, view_raw: bool = False):
        await self.search_rows(interaction, name, query, view_raw)

    @commands.command(name="view-row-by-value")
    async def table_view_data_prefix(self, ctx, name: str, query: str, view_raw: str = None):
        await self.search_rows(ctx, name, query, wants_raw(view_raw))


async def setup(bot):
    await bot.add_cog(View_Row_By_Value(bot))
