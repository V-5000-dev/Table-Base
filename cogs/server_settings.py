import discord
from discord.ext import commands
from discord import app_commands
import config
from config import CHECK, ADMIN, USER, MANAGER, PERMISSON, CommandType
from utils import verifyCommandPermissions, PageView, SelectRoles_Menu, SelectChannels_Menu, save_settings, send_page_view


class ToggleLoggingButton(discord.ui.Button):
    def __init__(self, ctx_or_interaction):
        super().__init__(label="Disable logs from unsuccessful command attempts", style=discord.ButtonStyle.grey)
        self.allowed_user = ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author
        self.guild_id = ctx_or_interaction.guild.id
        guild_settings = config.get_guild(self.guild_id)
        if not guild_settings["LOG_UNSUCCESSFUL"]:
            self.label = "Enable logs from unsuccessful command attempts"

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.allowed_user:
            await interaction.response.send_message(f"{PERMISSON} ``You did not invoke this command.``", ephemeral=True)
            return

        guild_settings = config.get_guild(self.guild_id)
        guild_settings["LOG_UNSUCCESSFUL"] = not guild_settings["LOG_UNSUCCESSFUL"]
        save_settings()

        self.label = (
            "Disable logs from unsuccessful command attempts"
            if guild_settings["LOG_UNSUCCESSFUL"]
            else "Enable logs from unsuccessful command attempts"
        )
        await interaction.response.edit_message(view=self.view)


def _channel_text(channels) -> str:
    return channels[0].mention if channels else "none"


async def save_serveradmin_roles(interaction, roles):
    guild_settings = config.get_guild(interaction.guild.id)
    guild_settings["SERVER_ADMIN_ROLE_IDS"] = [r.id for r in roles]
    save_settings()
    await interaction.response.send_message(
        f"{CHECK} ``Saved admin roles:`` {', '.join(r.name for r in roles) or 'none'}", ephemeral=True
    )


async def set_user_log_channel(interaction, channels):
    guild_settings = config.get_guild(interaction.guild.id)
    guild_settings["LOG_CHANNELS"][CommandType.USER] = channels[0].id if channels else 0
    save_settings()
    await interaction.response.send_message(
        f"{CHECK} ``User log channel set to:``{USER} {_channel_text(channels)}", ephemeral=True
    )


async def set_manager_log_channel(interaction, channels):
    guild_settings = config.get_guild(interaction.guild.id)
    guild_settings["LOG_CHANNELS"][CommandType.MANAGER] = channels[0].id if channels else 0
    save_settings()
    await interaction.response.send_message(
        f"{CHECK} ``Manager log channel set to:``{MANAGER} {_channel_text(channels)}", ephemeral=True
    )


async def set_admin_log_channel(interaction, channels):
    guild_settings = config.get_guild(interaction.guild.id)
    guild_settings["LOG_CHANNELS"][CommandType.ADMIN] = channels[0].id if channels else 0
    save_settings()
    await interaction.response.send_message(
        f"{CHECK} ``Admin log channel set to:``{ADMIN} {_channel_text(channels)}", ephemeral=True
    )


async def set_backup_channel(interaction, channels):
    guild_settings = config.get_guild(interaction.guild.id)
    guild_settings["TABLE_BACKUP_CHANNEL_ID"] = channels[0].id if channels else 0
    save_settings()
    await interaction.response.send_message(
        f"{CHECK} ``Server backups set to:`` {_channel_text(channels)}", ephemeral=True
    )


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

        embeds = [
            discord.Embed(title="Server Settings - Administration Permissions", description="Select which role(s) should have application-wide administration permissions. Users with these roles automatically receive admin permissions in all databases, and can create and delete databases. Roles that have Discord's administration permission enabled will also have this permission."),
            discord.Embed(title="Server Settings - User Log Channels", description="Select which channel should receive logs for unprotected user commands. Leaving this empty will prevent user commands from being logged."),
            discord.Embed(title="Server Settings - Management Log Channels", description="Select which channel should receive logs for protected database management commands. Leaving this empty will prevent database management commands from being logged."),
            discord.Embed(title="Server Settings - Administrative Log Channels", description="Select which channel should receive logs for protected database admin and server commands. Leaving this empty will prevent admin commands from being logged."),
            discord.Embed(title="Server Settings - Logging Settings", description="Toggle whether unsuccessful command logs from unauthorized users should be logged."),
            discord.Embed(title="Server Settings - Backups", description="Select which channel should receive a backup of this server's tables and settings every 24 hours. If you delete a table, you can find all of its information stored in the backup, allowing it to be recreated. Leaving this empty will turn backups off."),
        ]

        guild_settings = config.get_guild(ctx_or_interaction.guild.id)
        log_channels = guild_settings["LOG_CHANNELS"]

        view = PageView(
            embeds=embeds,
            ctx_or_interaction=ctx_or_interaction,
            page_menus={
                0: [lambda: SelectRoles_Menu(save_serveradmin_roles, ctx_or_interaction, guild_settings["SERVER_ADMIN_ROLE_IDS"])],
                1: [lambda: SelectChannels_Menu(set_user_log_channel, ctx_or_interaction, log_channels[CommandType.USER])],
                2: [lambda: SelectChannels_Menu(set_manager_log_channel, ctx_or_interaction, log_channels[CommandType.MANAGER])],
                3: [lambda: SelectChannels_Menu(set_admin_log_channel, ctx_or_interaction, log_channels[CommandType.ADMIN])],
                4: [lambda: ToggleLoggingButton(ctx_or_interaction)],
                5: [lambda: SelectChannels_Menu(set_backup_channel, ctx_or_interaction, guild_settings["TABLE_BACKUP_CHANNEL_ID"])],
            }
        )

        await send_page_view(ctx_or_interaction, view)


async def setup(bot):
    await bot.add_cog(Server_Settings(bot))