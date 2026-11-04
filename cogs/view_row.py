import discord
import io
from discord.ext import commands
from discord import app_commands
from config import ERROR, CommandType
from utils import authorize_table, format_row, respond, send_row_pages, table_name_autocomplete, wants_raw


class View_Row(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def build_row_file(self, table, name, row):
        """Builds a .txt file representation of a single row."""
        columns = table["column_names"]
        lines = [f"Table: {name}", ""]
        lines.append(" | ".join(str(c) for c in columns))
        lines.append("-" * 40)
        lines.append(" | ".join(str(cell) for cell in row))
        content = "\n".join(lines)
        buffer = io.BytesIO(content.encode("utf-8"))
        return discord.File(buffer, filename=f"{name}_row.txt")

    async def show_row(self, ctx_or_interaction, name: str, mention: str, view_raw: bool):
        table = await authorize_table(ctx_or_interaction, name, CommandType.USER)
        if table is None:
            return

        row = next((r for r in table["data"] if r[0] == mention), None)
        if row is None:
            await respond(ctx_or_interaction, f"{ERROR} ``You have no row in table`` ``{name}``.")
            return

        if view_raw:
            await respond(ctx_or_interaction, file=self.build_row_file(table, name, row))
            return

        await send_row_pages(
            ctx_or_interaction, f"Table: {name}", [format_row(table["column_names"], row)],
            intro="(Your row)", ephemeral=True
        )

    @app_commands.command(name="view-row", description="View your row in the table.")
    @app_commands.autocomplete(name=table_name_autocomplete)
    @app_commands.describe(view_raw="Send your row as a .txt file instead of an embed.")
    async def table_view_row(self, interaction: discord.Interaction, name: str, view_raw: bool = False):
        await self.show_row(interaction, name, interaction.user.mention, view_raw)

    @commands.command(name="view-row")
    async def table_view_row_prefix(self, ctx, name: str, view_raw: str = None):
        await self.show_row(ctx, name, ctx.author.mention, wants_raw(view_raw))


async def setup(bot):
    await bot.add_cog(View_Row(bot))
