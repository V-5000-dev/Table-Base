import discord
import config
from discord.ext import commands
from discord import app_commands
from config import GUILD_ID, CHECK, ERROR, CommandType
from utils import verifyCommandPermissions, save_settings


class Table_View_All(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="table-view-all", description="View the entire table.")
    async def table_view_all(self, interaction: discord.Interaction, name: str):
        if not await verifyCommandPermissions(interaction, CommandType.MANAGER):
            return

        table = next((t for t in config.ALL_TABLES if t["name"] == name), None)
        if table is None:
            await interaction.response.send_message(
                f"{ERROR} ``Table`` **{name}** ``not found.``", ephemeral=True
            )
            return

        columns = table["column_names"]
        rows = table["data"]

        if not columns:
            await interaction.response.send_message(
                f"{ERROR} ``Table`` **{name}** ``has no columns.``", ephemeral=True
            )
            return

        row_label_width = max(len(f"Row {len(rows)}"), len("Row")) if rows else len("Row")

        widths = [len(col) for col in columns]
        for row in rows:
            for i, cell in enumerate(row):
                widths[i] = max(widths[i], len(str(cell)))

        lines = []

        header_label = " " * row_label_width
        header_cells = " ".join(f"`{col.ljust(widths[i])}`" for i, col in enumerate(columns))
        lines.append(f"`{header_label}` {header_cells}")

        for row_index, row in enumerate(rows, start=1):
            label = f"Row {row_index}".ljust(row_label_width)
            row_cells = " ".join(f"`{str(cell).ljust(widths[i])}`" for i, cell in enumerate(row))
            lines.append(f"`{label}` {row_cells}")

        if not rows:
            lines.append("(no rows)")

        description = "\n".join(lines)

        embed = discord.Embed(
            title=f"Table: {name}",
            description=description
        )
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(Table_View_All(bot))