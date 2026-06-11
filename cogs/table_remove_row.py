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
    async def table_add_row(self, interaction: discord.Interaction, name: str):
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
                table["data"]["r"]
            




    @commands.command(name="table-remove-row")
    async def table_add_row_prefix(self, ctx, name: str, *values: str):
        if not await verifyCommandPermissions(ctx, CommandType.MANAGER):
            return

        table = next((t for t in config.ALL_TABLES if t["name"] == name), None)
        if table is None:
            await ctx.send(f"{ERROR} ``Table``  ``{name}`` ``not found.``")
            return

        new_row = ["None" for _ in range(table["columns"])]
        new_row[0] = ctx.author.mention
        new_row[1] = discord.utils.format_dt(discord.utils.utcnow())

        existing_index = next(
            (i for i, r in enumerate(table["data"]) if r[0] == ctx.author.mention),
            None
        )

        custom_columns = table["column_names"][2:]
        for i in range(len(custom_columns)):
            value = values[i] if i < len(values) else "None"

            if value.lower() == "none":
                if existing_index is not None:
                    new_row[2 + i] = table["data"][existing_index][2 + i]
                else:
                    new_row[2 + i] = "None"
            else:
                new_row[2 + i] = value

        if existing_index is not None:
            table["data"][existing_index] = new_row
            save_settings()
            await ctx.send(f"{CHECK} ``Your row in table`` ``{name}`` ``has been updated.``")
        else:
            table["data"].append(new_row)
            table["rows"] += 1
            save_settings()
            await ctx.send(f"{CHECK} ``Row added to table`` ``{name}``")


async def setup(bot):
    await bot.add_cog(Table_Remove_Row(bot))