import discord
import io
import config
from discord.ext import commands
from discord import app_commands
from config import GUILD_ID, CHECK, ERROR, CommandType
from utils import verifyCommandPermissions, save_settings, table_name_autocomplete


class Table_View(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def build_row_embed(self, table, name, row):
        columns = table["column_names"]
        embed = discord.Embed(title=f"Table: {name}", description="(Your row)")
        value = "\n".join(f"`{col}`: {cell}" for col, cell in zip(columns, row))
        embed.add_field(name="", value=value, inline=False)
        return embed

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

    @app_commands.command(name="table-view", description="View your row in the table.")
    @app_commands.autocomplete(name=table_name_autocomplete)
    @app_commands.describe(view_raw="Send your row as a .txt file instead of an embed.")
    async def table_view_row(self, interaction: discord.Interaction, name: str, view_raw: bool = False):
        if not await verifyCommandPermissions(interaction, CommandType.USER):
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

        row = next((r for r in table["data"] if r[0] == interaction.user.mention), None)
        if row is None:
            await interaction.response.send_message(
                f"{ERROR} ``You have no row in table`` ``{name}``.", ephemeral=True
            )
            return

        if view_raw:
            await interaction.response.send_message(file=self.build_row_file(table, name, row), ephemeral=True)
            return

        await interaction.response.send_message(embed=self.build_row_embed(table, name, row), ephemeral=True)

    @commands.command(name="table-view")
    async def table_view_row_prefix(self, ctx, name: str, view_raw: str = None):
        if not await verifyCommandPermissions(ctx, CommandType.USER):
            return

        guild_settings = config.get_guild(ctx.guild.id)
        table = next((t for t in guild_settings["ALL_TABLES"] if t["name"] == name), None)
        if table is None:
            await ctx.send(f"{ERROR} ``Table`` ``{name}`` ``not found.``")
            return

        if not table["column_names"]:
            await ctx.send(f"{ERROR} ``Table`` ``{name}`` ``has no columns.``")
            return

        row = next((r for r in table["data"] if r[0] == ctx.author.mention), None)
        if row is None:
            await ctx.send(f"{ERROR} ``You have no row in table`` ``{name}``.")
            return

        if view_raw and view_raw.lower() in ("file", "txt", "true"):
            await ctx.send(file=self.build_row_file(table, name, row))
            return

        await ctx.send(embed=self.build_row_embed(table, name, row))


async def setup(bot):
    await bot.add_cog(Table_View(bot))