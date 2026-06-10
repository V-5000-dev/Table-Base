import discord
import config
from discord.ext import commands
from discord import app_commands
from config import GUILD_ID, CHECK, ERROR, CommandType
from utils import verifyCommandPermissions, save_settings


class Table_Add_Row(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="table-add-row", description="Add a row to the table.")
    async def table_add_row(self, interaction: discord.Interaction, name: str):
        if not await verifyCommandPermissions(interaction, CommandType.MANAGER):
            return

        table = next((t for t in config.ALL_TABLES if t["name"] == name), None)
        if table is None:
            await interaction.response.send_message(
                f"{ERROR} ``Table`` **{name}** ``not found.``", ephemeral=True
            )
            return

        new_row = ["" for _ in range(table["columns"])]
        new_row[0] = interaction.user.mention
        new_row[1] = discord.utils.format_dt(discord.utils.utcnow())

        table["data"].append(new_row)
        table["rows"] += 1
        save_settings()

        await interaction.response.send_message(
            f"{CHECK} ``Row added to table`` **{name}**", ephemeral=True
        )

    @commands.command(name="table-add-row")
    async def table_add_row_prefix(self, ctx, name: str):
        if not await verifyCommandPermissions(ctx, CommandType.MANAGER):
            return

        table = next((t for t in config.ALL_TABLES if t["name"] == name), None)
        if table is None:
            await ctx.send(f"{ERROR} ``Table`` **{name}** ``not found.``")
            return

        new_row = ["" for _ in range(table["columns"])]
        new_row[0] = ctx.author.mention
        new_row[1] = discord.utils.format_dt(discord.utils.utcnow())

        table["data"].append(new_row)
        table["rows"] += 1
        save_settings()

        await ctx.send(f"{CHECK} ``Row added to table`` **{name}**")


async def setup(bot):
    await bot.add_cog(Table_Add_Row(bot))