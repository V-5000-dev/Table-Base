import discord
from discord.ext import commands
from discord import app_commands
from config import CHECK, ERROR, CommandType
from utils import authorize_table, find_row_index, respond, save_settings, table_name_autocomplete


class Remove_Row_By_User(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def remove_row(self, ctx_or_interaction, name: str, user: discord.Member):
        table = await authorize_table(ctx_or_interaction, name, CommandType.ADMIN)
        if table is None:
            return

        index = find_row_index(table, user.mention)
        if index is None:
            await respond(ctx_or_interaction, f"{ERROR} ``Failed to find`` {user.mention} ``'s row in table`` ``{name}``")
            return

        del table["data"][index]
        table["rows"] -= 1
        save_settings()
        await respond(ctx_or_interaction, f"{CHECK} ``Removed`` {user.mention} ``'s row from table`` ``{name}``")

    @app_commands.command(name="remove-row-by-user", description="Remove another user's row from the Table.")
    @app_commands.autocomplete(name=table_name_autocomplete)
    async def table_remove_row_user(self, interaction: discord.Interaction, name: str, user: discord.Member):
        await self.remove_row(interaction, name, user)

    @commands.command(name="remove-row-by-user")
    async def table_remove_row_prefix(self, ctx, name: str, user: discord.Member):
        await self.remove_row(ctx, name, user)


async def setup(bot):
    await bot.add_cog(Remove_Row_By_User(bot))
