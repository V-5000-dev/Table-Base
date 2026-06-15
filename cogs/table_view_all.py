import discord
import io
import config
from discord.ext import commands
from discord import app_commands
from config import GUILD_ID, CHECK, ERROR, CommandType
from utils import verifyCommandPermissions, save_settings, table_name_autocomplete, PageView


ROWS_PER_PAGE = 10  # embeds max at 25 fields, keep some headroom


class Table_View_Full(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def build_table_embeds(self, table, name):
        columns = table["column_names"]
        rows = table["data"]

        if not columns:
            return None

        if not rows:
            embed = discord.Embed(title=f"Table: {name}", description="(no rows)")
            return [embed]

        embeds = []
        chunks = [rows[i:i + ROWS_PER_PAGE] for i in range(0, len(rows), ROWS_PER_PAGE)]

        for chunk_index, chunk in enumerate(chunks):
            embed = discord.Embed(title=f"Table: {name}")
            start_row = chunk_index * ROWS_PER_PAGE + 1

            for offset, row in enumerate(chunk):
                row_index = start_row + offset
                value = "\n".join(f"`{col}`: {cell}" for col, cell in zip(columns, row))
                embed.add_field(name=f"Row {row_index}", value=value, inline=False)

            embeds.append(embed)

        return embeds

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
            # Header
            lines.append(" | ".join(str(c) for c in columns))
            lines.append("-" * 40)

            # Rows
            for row_index, row in enumerate(rows, start=1):
                row_str = " | ".join(str(cell) for cell in row)
                lines.append(f"{row_index}: {row_str}")

        content = "\n".join(lines)
        buffer = io.BytesIO(content.encode("utf-8"))
        return discord.File(buffer, filename=f"{name}.txt")

    @app_commands.command(name="table-view-full", description="View the entire table.")
    @app_commands.autocomplete(name=table_name_autocomplete)
    @app_commands.describe(view_raw="Send the table as a .txt file instead of an embed.")
    async def table_view_all(self, interaction: discord.Interaction, name: str, view_raw: bool = False):
        if not await verifyCommandPermissions(interaction, CommandType.MANAGER):
            return

        table = next((t for t in config.ALL_TABLES if t["name"] == name), None)
        if table is None:
            await interaction.response.send_message(
                f"{ERROR} ``Table`` ``{name}`` ``not found.``", ephemeral=True
            )
            return

        if view_raw:
            file = self.build_table_file(table, name)
            await interaction.response.send_message(file=file)
            return

        embeds = self.build_table_embeds(table, name)

        if embeds is None:
            await interaction.response.send_message(
                f"{ERROR} ``Table`` ``{name}`` ``has no columns.``", ephemeral=True
            )
            return

        if len(embeds) == 1:
            await interaction.response.send_message(embed=embeds[0])
        else:
            view = PageView(embeds=embeds, ctx_or_interaction=interaction)
            await interaction.response.send_message(embed=embeds[0], view=view)

    @commands.command(name="table-view-full")
    async def table_view_all_prefix(self, ctx, name: str, view_raw: str = None):
        if not await verifyCommandPermissions(ctx, CommandType.MANAGER):
            return

        table = next((t for t in config.ALL_TABLES if t["name"] == name), None)
        if table is None:
            await ctx.send(f"{ERROR} ``Table`` ``{name}`` ``not found.``")
            return

        if view_raw and view_raw.lower() in ("file", "txt", "true"):
            file = self.build_table_file(table, name)
            await ctx.send(file=file)
            return

        embeds = self.build_table_embeds(table, name)

        if embeds is None:
            await ctx.send(f"{ERROR} ``Table`` ``{name}`` ``has no columns.``")
            return

        if len(embeds) == 1:
            await ctx.send(embed=embeds[0])
        else:
            view = PageView(embeds=embeds, ctx_or_interaction=ctx)
            await ctx.send(embed=embeds[0], view=view)


async def setup(bot):
    await bot.add_cog(Table_View_Full(bot))