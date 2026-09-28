import discord
import config
from discord.ext import commands
from discord import app_commands
from config import CHECK, ERROR, CommandType
from utils import verifyCommandPermissions, save_settings, table_name_autocomplete


class Remove_Row_By_ID(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="remove-row-by-id", description="Remove a row from the table by row number.")
    @app_commands.autocomplete(name=table_name_autocomplete)
    async def table_remove_row(self, interaction: discord.Interaction, name: str, row: int):
        if not await verifyCommandPermissions(interaction, CommandType.MANAGER):
            return

        settings = config.get_guild(interaction.guild_id)
        table = next((t for t in settings["ALL_TABLES"] if t["name"] == name), None)
        if table is None:
            await interaction.response.send_message(
                f"{ERROR} ``Table`` ``{name}`` ``not found.``", ephemeral=True
            )
            return

        if row < 1 or row > len(table["data"]):
            await interaction.response.send_message(
                f"{ERROR} ``Row number must be between 1 and {len(table['data'])}.``", ephemeral=True
            )
            return

        del table["data"][row - 1]
        table["rows"] -= 1
        save_settings()
        await interaction.response.send_message(
            f"{CHECK} ``Removed row {row} from table`` ``{name}``.", ephemeral=True
        )

    @commands.command(name="remove-row-by-id")
    async def table_remove_row_prefix(self, ctx, name: str, row: int):
        if not await verifyCommandPermissions(ctx, CommandType.MANAGER):
            return

        settings = config.get_guild(ctx.guild.id)
        table = next((t for t in settings["ALL_TABLES"] if t["name"] == name), None)
        if table is None:
            await ctx.send(f"{ERROR} ``Table`` ``{name}`` ``not found.``")
            return

        if row < 1 or row > len(table["data"]):
            await ctx.send(f"{ERROR} ``Row number must be between 1 and {len(table['data'])}.``")
            return

        del table["data"][row - 1]
        table["rows"] -= 1
        save_settings()
        await ctx.send(f"{CHECK} ``Removed row {row} from table`` ``{name}``.")


async def setup(bot):
    await bot.add_cog(Remove_Row_By_ID(bot))
