import discord
from discord.ext import commands
from discord import app_commands
import config
from config import GUILD_ID, CHECK, ADMIN, USER, MANAGER,PERMISSON, CommandType
from utils import verifyCommandPermissions, PageView, SelectRoles_Menu, SelectChannels_Menu, save_settings

class ToggleLoggingButton(discord.ui.Button):
    def __init__(self, ctx_or_interaction):
        super().__init__(label="Disable logs from unsuccessful command attempts", style=discord.ButtonStyle.grey)
        self.state = False
        self.allowed_user = ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.allowed_user:
            await interaction.response.send_message(f"{PERMISSON} ``You did not invoke this command.``", ephemeral=True)
            return
        self.state = not self.state
        config.LOG_UNSUCCESSFUL = not self.state
        save_settings()
        self.label = "Enable logs from unsuccessful command attempts" if self.state else "Disable logs from unsuccessful command attempts"
        await interaction.response.edit_message(view=self.view)


async def save_serveradmin_roles(interaction, roles):
    config.SERVER_ADMIN_ROLE_IDS = [r.id for r in roles]
    save_settings()
    await interaction.response.send_message(f"{CHECK} ``Saved admin roles:`` {', '.join(r.name for r in roles)}", ephemeral=True)


async def set_user_log_channel(interaction, channels):
    if not channels: return
    config.LOG_CHANNELS[CommandType.USER] = channels[0].id
    save_settings()
    await interaction.response.send_message(f"{CHECK} ``User log channel set to:``{USER} {channels[0].mention}", ephemeral=True)


async def set_manager_log_channel(interaction, channels):
    if not channels: return
    config.LOG_CHANNELS[CommandType.MANAGER] = channels[0].id
    save_settings()
    await interaction.response.send_message(f"{CHECK} ``Manager log channel set to:``{MANAGER} {channels[0].mention}", ephemeral=True)


async def set_admin_log_channel(interaction, channels):
    if not channels: return
    config.LOG_CHANNELS[CommandType.ADMIN] = channels[0].id
    save_settings()
    await interaction.response.send_message(f"{CHECK} ``Admin log channel set to:``{ADMIN} {channels[0].mention}", ephemeral=True)
class Server_Settings(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="server-settings", description="Configure the settings for server.")
    async def server_settings(self, interaction: discord.Interaction):
        await self._server_settings_logic(interaction)

    @commands.command(name="server-settings")
    async def server_settings_prefix(self, ctx):
        await self._server_settings_logic(ctx)

    async def _server_settings_logic(self, ctx_or_interaction):
        if not await verifyCommandPermissions(ctx_or_interaction, CommandType.SERVER_ADMIN):
            return

        guild = ctx_or_interaction.guild

        embeds = [
            discord.Embed(title="Server Settings - Administration Permissions", description="Select which role(s) should have application-wide administration permissions. Users with these roles automatically receive admin permissions in all databases, and can create and delete databases. Roles that have Discord's administration permission enabled will also have this permission."),
            discord.Embed(title="Server Settings - User Log Channels", description="Select which channel should receive logs for unprotected user commands. Leaving this empty will prevent user commands from being logged."),
            discord.Embed(title="Server Settings - Management Log Channels", description="Select which channel should receive logs for protected database management commands. Leaving this empty will prevent database management commands from being logged."),
            discord.Embed(title="Server Settings - Administrative Log Channels", description="Select which channel should receive logs for protected database admin and server commands. Leaving this empty will prevent admin commands from being logged."),
            discord.Embed(title="Server Settings - Logging Settings", description="Toggle whether unsuccessful command logs from unauthorized users should be logged."),
        ]

        view = PageView(
            embeds=embeds,
            ctx_or_interaction=ctx_or_interaction,
            page_menus={
                0: [lambda: SelectRoles_Menu(save_serveradmin_roles, ctx_or_interaction)],
                1: [lambda: SelectChannels_Menu(set_user_log_channel, ctx_or_interaction)],
                2: [lambda: SelectChannels_Menu(set_manager_log_channel, ctx_or_interaction)],
                3: [lambda: SelectChannels_Menu(set_admin_log_channel, ctx_or_interaction)],
                4: [lambda: ToggleLoggingButton(ctx_or_interaction)],
            }
        )

        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.response.send_message(embed=embeds[0], view=view)
        else:
            await ctx_or_interaction.send(embed=embeds[0], view=view)

async def setup(bot):
    await bot.add_cog(Server_Settings(bot))