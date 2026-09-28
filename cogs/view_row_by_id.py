import discord
import io
import config
from discord.ext import commands
from discord import app_commands
from config import CHECK, ERROR, CommandType
from utils import verifyCommandPermissions, table_name_autocomplete


class Table_View_Row_By_ID(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def build_row_embed(self, table, name, row_number, row):
        columns = table["column_names"]
        embed = discord.Embed(title=f"Table: {name} | Row {row_number}")
        value = "\n".join(f"`{col}`: {cell}" for col, cell in zip(columns, row))
        embed.add_field(name="", value=value, inline=False)
        return embed

    def build_row_file(self, table, name, row_number, row):
        columns = table["column_names"]
        lines = [f"Table: {name} | Row {row_number}", ""]
        lines.append(" | ".join(str(c) for c in columns))
        lines.append("-" * 40)
        lines.append(" | ".join(str(cell) for cell in row))
        content = "\n".join(lines)
        buffer = io.BytesIO(content.encode("utf-8"))
        return discord.File(buffer, filename=f"{name}_row_{row_number}.txt")

    def get_row(self, guild_id, name, row_number):
        """Returns (table, row, error_message). error_message is None on success."""
        settings = config.get_guild(guild_id)
        table = next((t for t in settings["ALL_TABLES"] if t["name"] == name), None)
        if table is None:
            return None, None, f"{ERROR} ``Table`` ``{name}`` ``not found.``"

        if not table["column_names"]:
            return None, None, f"{ERROR} ``Table`` ``{name}`` ``has no columns.``"

        if not table["data"]:
            return None, None, f"{ERROR} ``Table`` ``{name}`` ``has no rows.``"

        if row_number < 1 or row_number > len(table["data"]):
            return None, None, f"{ERROR} ``Row number must be between 1 and {len(table['data'])}.``"

        return table, table["data"][row_number - 1], None

    @app_commands.command(name="view-row-by-id", description="View a row in the table by row number.")
    @app_commands.autocomplete(name=table_name_autocomplete)
    @app_commands.describe(row="The row number (starting at 1).", view_raw="Send the row as a .txt file instead of an embed.")
    async def table_view_row_by_id(self, interaction: discord.Interaction, name: str, row: int, view_raw: bool = False):
        if not await verifyCommandPermissions(interaction, CommandType.MANAGER):
            return

        table, row_data, error = self.get_row(interaction.guild_id, name, row)
        if error:
            await interaction.response.send_message(error, ephemeral=True)
            return

        if view_raw:
            await interaction.response.send_message(file=self.build_row_file(table, name, row, row_data))
            return

        await interaction.response.send_message(embed=self.build_row_embed(table, name, row, row_data))

    @commands.command(name="view-row-by-id")
    async def table_view_row_by_id_prefix(self, ctx, name: str, row: int, view_raw: str = None):
        if not await verifyCommandPermissions(ctx, CommandType.MANAGER):
            return

        table, row_data, error = self.get_row(ctx.guild.id, name, row)
        if error:
            await ctx.send(error)
            return

        if view_raw and view_raw.lower() in ("file", "txt", "true"):
            await ctx.send(file=self.build_row_file(table, name, row, row_data))
            return

        await ctx.send(embed=self.build_row_embed(table, name, row, row_data))


async def setup(bot):
    await bot.add_cog(View_Row_By_ID(bot))