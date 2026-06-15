import discord
import config
from discord.ext import commands
from discord import app_commands
from config import GUILD_ID, CHECK, ERROR, CommandType
from utils import verifyCommandPermissions, save_settings, table_name_autocomplete



class Table_Remove_Row(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="table-remove-row", description="Remove your row from the table.")
    @app_commands.autocomplete(name=table_name_autocomplete)
    async def table_remove_row(self, interaction: discord.Interaction, name: str):
        if not await verifyCommandPermissions(interaction, CommandType.MANAGER):
            return

        table = next((t for t in config.ALL_TABLES if t["name"] == name), None)
        if table is None:
            await interaction.response.send_message(
                f"{ERROR} ``Table`` ``{name}`` ``not found.``", ephemeral=True
            )
            return

        for i, r in enumerate(table["data"]):
            if r[0] == interaction.user.mention:
                del table["data"][i]
                table["rows"] -= 1
                save_settings()
                await interaction.response.send_message(
                    f"{CHECK} ``Removed your row from table`` ``{name}`` ``.``", ephemeral=True
                )
                return

        await interaction.response.send_message(
            f"{ERROR} ``Failed to find your row in table`` ``{name}``", ephemeral=True
        )

    @commands.command(name="table-remove-row")
    async def table_remove_row_prefix(self, ctx, name: str):
        if not await verifyCommandPermissions(ctx, CommandType.MANAGER):
            return

        table = next((t for t in config.ALL_TABLES if t["name"] == name), None)
        if table is None:
            await ctx.send(f"{ERROR} ``Table`` ``{name}`` ``not found.``")
            return

        for i, r in enumerate(table["data"]):
            if r[0] == ctx.author.mention:
                del table["data"][i]
                table["rows"] -= 1
                save_settings()
                await ctx.send(f"{CHECK} ``Removed your row from table`` ``{name}``")
                return

        await ctx.send(f"{ERROR} ``Failed to find your row in table`` ``{name}``")


async def setup(bot):
    await bot.add_cog(Table_Remove_Row(bot))