import discord
import config
from discord.ext import commands
from discord import app_commands
from config import GUILD_ID, CHECK, ERROR, X, CommandType
from utils import verifyCommandPermissions, save_settings, table_name_autocomplete


class DeleteTableConfirm(discord.ui.View):
    def __init__(self, table: dict, requester: discord.Member, guild_id: int):
        super().__init__(timeout=60)
        self.table = table
        self.requester = requester
        self.guild_id = guild_id

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        if self.message:
            await self.message.edit(content=f"{ERROR} ``Table deletion timed out.``", view=self)

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.grey, emoji=f"{CHECK}")
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.requester:
            await interaction.response.send_message(
                f"{ERROR} ``You cannot interact with other people's embeds.``", ephemeral=True
            )
            return

        settings = config.get_guild(self.guild_id)
        settings["ALL_TABLES"].remove(self.table)
        save_settings()

        for child in self.children:
            child.disabled = True

        await interaction.response.edit_message(
            content=f"{CHECK} ``Table`` ``{self.table['name']}`` ``has been deleted.``", view=self
        )

    @discord.ui.button(label="Return", style=discord.ButtonStyle.grey, emoji=f"{X}")
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.requester:
            await interaction.response.send_message(
                f"{ERROR} ``You cannot interact with other people's embeds.``", ephemeral=True
            )
            return

        for child in self.children:
            child.disabled = True

        await interaction.response.edit_message(
            content=f"{CHECK} ``Table deletion cancelled.``", view=self
        )


class Table_Delete(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="table-delete", description="Delete a table.")
    @app_commands.autocomplete(name=table_name_autocomplete)
    async def table_delete(self, interaction: discord.Interaction, name: str):
        if not await verifyCommandPermissions(interaction, CommandType.SERVER_ADMIN):
            return

        settings = config.get_guild(interaction.guild_id)
        table = next((t for t in settings["ALL_TABLES"] if t["name"] == name), None)
        if table is None:
            await interaction.response.send_message(
                f"{ERROR} ``Table`` ``{name}`` ``not found.``", ephemeral=True
            )
            return

        view = DeleteTableConfirm(table, interaction.user, interaction.guild_id)
        await interaction.response.send_message(
            f"{ERROR} ``Are you sure you want to delete table`` ``{name}`` ``? This cannot be undone.``",
            view=view,
            ephemeral=True
        )
        view.message = await interaction.original_response()

    @commands.command(name="table-delete")
    async def table_delete_prefix(self, ctx, name: str):
        if not await verifyCommandPermissions(ctx, CommandType.SERVER_ADMIN):
            return

        settings = config.get_guild(ctx.guild.id)
        table = next((t for t in settings["ALL_TABLES"] if t["name"] == name), None)
        if table is None:
            await ctx.send(f"{ERROR} ``Table`` ``{name}`` ``not found.``")
            return

        view = DeleteTableConfirm(table, ctx.author, ctx.guild.id)
        view.message = await ctx.send(
            f"{ERROR} ``Are you sure you want to delete table`` ``{name}`` ``? This cannot be undone.``",
            view=view
        )

async def setup(bot):
    await bot.add_cog(Table_Delete(bot))