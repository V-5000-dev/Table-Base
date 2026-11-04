import discord
from discord.ext import commands
from discord import app_commands
from config import CHECK, ERROR, CommandType
from utils import authorize_table, respond, save_settings, table_name_autocomplete


class Remove_Row_By_ID(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def remove_row(self, ctx_or_interaction, name: str, row: int):
        table = await authorize_table(ctx_or_interaction, name, CommandType.ADMIN)
        if table is None:
            return

        if row < 1 or row > len(table["data"]):
            await respond(ctx_or_interaction, f"{ERROR} ``Row number must be between 1 and {len(table['data'])}.``")
            return

        del table["data"][row - 1]
        table["rows"] -= 1
        save_settings()
        await respond(ctx_or_interaction, f"{CHECK} ``Removed row {row} from table`` ``{name}``.")

    @app_commands.command(name="remove-row-by-id", description="Remove a row from the table by row number.")
    @app_commands.autocomplete(name=table_name_autocomplete)
    async def table_remove_row(self, interaction: discord.Interaction, name: str, row: int):
        await self.remove_row(interaction, name, row)

    @commands.command(name="remove-row-by-id")
    async def table_remove_row_prefix(self, ctx, name: str, row: int):
        await self.remove_row(ctx, name, row)


async def setup(bot):
    await bot.add_cog(Remove_Row_By_ID(bot))
