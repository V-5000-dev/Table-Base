import discord
import config
from discord.ext import commands
from discord import app_commands
from config import CHECK, ERROR, CommandType
from utils import respond, save_settings, table_name_error, verifyCommandPermissions


class Create_Table(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def create_table(self, ctx_or_interaction, name: str):
        if not await verifyCommandPermissions(ctx_or_interaction, CommandType.SERVER_ADMIN):
            return

        name = name.strip()
        guild_settings = config.get_guild(ctx_or_interaction.guild.id)

        error = table_name_error(name)
        if error:
            await respond(ctx_or_interaction, f"{ERROR} ``{error}``")
            return
        if any(t["name"] == name for t in guild_settings["ALL_TABLES"]):
            await respond(ctx_or_interaction, f"{ERROR} ``A table with the name`` ``{name}`` ``already exists.``")
            return
        if len(guild_settings["ALL_TABLES"]) >= 20:
            await respond(ctx_or_interaction, f"{ERROR} ``The maximum of 20 tables has been reached.``")
            return

        table = {
            "name": name,
            "rows": 0,
            "columns": 2,
            "column_names": ["User", "Timestamp"],
            "member_role_ids": [],
            "ping_managers": True,
            "data": []
        }
        guild_settings["ALL_TABLES"].append(table)
        save_settings()

        await respond(
            ctx_or_interaction,
            f"{CHECK} ``Table with the name`` ``{name}`` ``created.``\n``Set up the table with`` ``table-settings``",
            ephemeral=False
        )

    @app_commands.command(name="create-table", description="Create a new table.")
    async def table_create(self, interaction: discord.Interaction, name: str):
        await self.create_table(interaction, name)

    @commands.command(name="create-table")
    async def table_create_prefix(self, ctx, name: str):
        await self.create_table(ctx, name)


async def setup(bot):
    await bot.add_cog(Create_Table(bot))
