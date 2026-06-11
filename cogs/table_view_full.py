import discord
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

    @app_commands.command(name="table-view-full", description="View the entire table.")
    @app_commands.autocomplete(name=table_name_autocomplete)
    async def table_view_all(self, interaction: discord.Interaction, name: str):
        if not await verifyCommandPermissions(interaction, CommandType.MANAGER):
            return

        table = next((t for t in config.ALL_TABLES if t["name"] == name), None)
        if table is None:
            await interaction.response.send_message(
                f"{ERROR} ``Table`` ``{name}`` ``not found.``", ephemeral=True
            )
            return

        embeds = self.build_table_embeds(table, name)


        if len(embeds) == 1:
            await interaction.response.send_message(embed=embeds[0])
        else:
            view = PageView(embeds=embeds, ctx_or_interaction=interaction)
            await interaction.response.send_message(embed=embeds[0], view=view)

    @commands.command(name="table-view-full")
    async def table_view_all_prefix(self, ctx, name: str):
        if not await verifyCommandPermissions(ctx, CommandType.MANAGER):
            return

        table = next((t for t in config.ALL_TABLES if t["name"] == name), None)
        if table is None:
            await ctx.send(f"{ERROR} ``Table`` ``{name}`` ``not found.``")
            return

        embeds = self.build_table_embeds(table, name)

        if len(embeds) == 1:
            await ctx.send(embed=embeds[0])
        else:
            view = PageView(embeds=embeds, ctx_or_interaction=ctx)
            await ctx.send(embed=embeds[0], view=view)


async def setup(bot):
    await bot.add_cog(Table_View_Full(bot))