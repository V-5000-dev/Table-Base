import discord
import config
from discord.ext import commands
from discord import app_commands
from config import GUILD_ID, CHECK, ERROR, CommandType
from utils import verifyCommandPermissions, save_settings, table_name_autocomplete


class Table_View_Full(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def build_table_embed(self, table, name):
        columns = table["column_names"]
        rows = table["data"]

        if not columns:
            return None

        timestamp_index = columns.index("Timestamp") if "Timestamp" in columns else None

        row_label_width = max(len(f"Row {len(rows)}"), len("Row")) if rows else len("Row")

        widths = []
        for i, col in enumerate(columns):
            if i == timestamp_index:
                widths.append(0)
                continue
            w = len(col)
            for row in rows:
                w = max(w, len(str(row[i])))
            widths.append(w)

        def format_cell(i, value):
            if i == timestamp_index:
                return str(value)
            return f"`{str(value).ljust(widths[i])}`"

        lines = []

        header_num = "#".ljust(row_label_width)
        header_cells = " ".join(format_cell(i, col) for i, col in enumerate(columns))
        lines.append(f"`{header_num}` {header_cells}")

        for row_index, row in enumerate(rows, start=1):
            label = f"Row {row_index}".ljust(row_label_width)
            row_cells = " ".join(format_cell(i, cell) for i, cell in enumerate(row))
            lines.append(f"`{label}` {row_cells}")

        if not rows:
            lines.append("(no rows)")

        description = "\n".join(lines)

        return discord.Embed(
            title=f"Table: {name}",
            description=description
        )

    @app_commands.command(name="table-view-all", description="View the entire table.")
    @app_commands.autocomplete(name=table_name_autocomplete)
    async def table_view_all(self, interaction: discord.Interaction, name: str):
        if not await verifyCommandPermissions(interaction, CommandType.MANAGER):
            return

        table = next((t for t in config.ALL_TABLES if t["name"] == name), None)
        if table is None:
            await interaction.response.send_message(
                f"{ERROR} ``Table`` **{name}** ``not found.``", ephemeral=True
            )
            return

        embed = self.build_table_embed(table, name)
        if embed is None:
            await interaction.response.send_message(
                f"{ERROR} ``Table`` **{name}** ``has no columns.``", ephemeral=True
            )
            return

        await interaction.response.send_message(embed=embed)

    @commands.command(name="table-view-all")
    async def table_view_all_prefix(self, ctx, name: str):
        if not await verifyCommandPermissions(ctx, CommandType.MANAGER):
            return

        table = next((t for t in config.ALL_TABLES if t["name"] == name), None)
        if table is None:
            await ctx.send(f"{ERROR} ``Table`` **{name}** ``not found.``")
            return

        embed = self.build_table_embed(table, name)
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Table_View_Full(bot))