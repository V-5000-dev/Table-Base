import discord
import config
from discord.ext import commands
from discord import app_commands
from config import GUILD_ID, CHECK, ERROR, CommandType
from utils import verifyCommandPermissions, save_settings


class Table_Create(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="table-create", description="Create a new table.")
    async def table_create(self, interaction: discord.Interaction, name: str):
        if not await verifyCommandPermissions(interaction, CommandType.SERVER_ADMIN):
            return

        guild_settings = config.get_guild(interaction.guild.id)

        if any(t["name"] == name for t in guild_settings["ALL_TABLES"]):
            await interaction.response.send_message(
                f"{ERROR} ``A table with the name`` ``{name}`` ``already exists.``", ephemeral=True
            )
            return
        if len(guild_settings["ALL_TABLES"]) >= 20:
            await interaction.response.send_message(
                f"{ERROR} ``The maximum of 20 tables has been reached.``", ephemeral=True
            )
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

        await interaction.response.send_message(
            f"{CHECK} ``Table with the name`` ``{name}`` ``created.``\n``Set up the table with`` ``table-settings``"
        )

    @commands.command(name="table-create")
    async def table_create_prefix(self, ctx, name: str):
        if not await verifyCommandPermissions(ctx, CommandType.SERVER_ADMIN):
            return

        guild_settings = config.get_guild(ctx.guild.id)

        if any(t["name"] == name for t in guild_settings["ALL_TABLES"]):
            await ctx.send(f"{ERROR} ``A table with the name`` ``{name}`` ``already exists.``")
            return
        if len(guild_settings["ALL_TABLES"]) >= 20:
            await ctx.send(f"{ERROR} ``The maximum of 20 tables has been reached.``")
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

        await ctx.send(
            f"{CHECK} ``Table with the name`` ``{name}`` ``created.``\n``Set up the table with`` ``table-settings``"
        )


async def setup(bot):
    await bot.add_cog(Table_Create(bot))