import discord
import io
import config
from discord.ext import commands
from discord import app_commands
from config import GUILD_ID, CHECK, ERROR, CommandType
from utils import verifyCommandPermissions, save_settings, table_name_autocomplete


class Table_View_Data(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def build_rows_embed(self, table, name, matches):
        columns = table["column_names"]
        embed = discord.Embed(title=f"Table: {name}", description=f"Found {len(matches)} matching row(s)")
        for row_num, row in matches:
            value = "\n".join(f"`{col}`: {cell}" for col, cell in zip(columns, row))
            embed.add_field(name=f"Row {row_num}", value=value, inline=False)
        return embed

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

    @app_commands.command(name="table-view-data", description="Search for a value across all rows in a table.")
    @app_commands.autocomplete(name=table_name_autocomplete)
    @app_commands.describe(
        query="The value to search for.",
        view_raw="Send results as a .txt file instead of an embed."
    )
    async def table_view_data(self, interaction: discord.Interaction, name: str, query: str, view_raw: bool = False):
        if not await verifyCommandPermissions(interaction, CommandType.MANAGER):
            return

        guild_settings = config.get_guild(interaction.guild.id)
        table = next((t for t in guild_settings["ALL_TABLES"] if t["name"] == name), None)
        if table is None:
            await interaction.response.send_message(
                f"{ERROR} ``Table`` ``{name}`` ``not found.``", ephemeral=True
            )
            return

        if not table["column_names"]:
            await interaction.response.send_message(
                f"{ERROR} ``Table`` ``{name}`` ``has no columns.``", ephemeral=True
            )
            return

        matches = [
            (i + 1, row)
            for i, row in enumerate(table["data"])
            if any(query.lower() in str(cell).lower() for cell in row)
        ]
        if not matches:
            await interaction.response.send_message(
                f"{ERROR} ``No rows found containing`` ``{query}``.", ephemeral=True
            )
            return

        if view_raw:
            await interaction.response.send_message(file=self.build_rows_file(table, name, [r for _, r in matches]))
            return

        embed = self.build_rows_embed(table, name, matches)
        if len(embed) > 6000:
            await interaction.response.send_message(
                f"{ERROR} ``Too many results to display as embed. Use`` ``view_raw=True``.", ephemeral=True
            )
            return

        await interaction.response.send_message(embed=embed)


    @commands.command(name="table-view-data")
    async def table_view_data_prefix(self, ctx, name: str, query: str, view_raw: str = None):
        if not await verifyCommandPermissions(ctx, CommandType.MANAGER):
            return

        guild_settings = config.get_guild(ctx.guild.id)
        table = next((t for t in guild_settings["ALL_TABLES"] if t["name"] == name), None)
        if table is None:
            await ctx.send(f"{ERROR} ``Table`` ``{name}`` ``not found.``")
            return

        if not table["column_names"]:
            await ctx.send(f"{ERROR} ``Table`` ``{name}`` ``has no columns.``")
            return

        matches = [
            (i + 1, row)
            for i, row in enumerate(table["data"])
            if any(query.lower() in str(cell).lower() for cell in row)
        ]
        if not matches:
            await ctx.send(f"{ERROR} ``No rows found containing`` ``{query}``.")
            return

        if view_raw and view_raw.lower() in ("file", "txt", "true"):
            await ctx.send(file=self.build_rows_file(table, name, [r for _, r in matches]))
            return

        embed = self.build_rows_embed(table, name, matches)
        if len(embed) > 6000:
            await ctx.send(f"{ERROR} ``Too many results to display as embed. Use`` ``view_raw=True``.")
            return

        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Table_View_Data(bot))