import discord
from discord.ext import commands
from discord import app_commands
import config
from config import GUILD_ID, CHECK, ADMIN, USER, MANAGER, PERMISSON, ERROR, CommandType
from utils import verifyCommandPermissions, PageView, SelectRoles_Menu, SelectChannels_Menu, save_settings, table_name_autocomplete


class AddColumn_Input(discord.ui.Modal, title="Add Column"):
    column_name = discord.ui.TextInput(
        label="Enter a name for the column",
        placeholder="Type here...",
        required=True,
        max_length=50
    )

    def __init__(self, table: dict):
        super().__init__()
        self.table = table

    async def on_submit(self, interaction: discord.Interaction):
        name = self.column_name.value
        if name in self.table["column_names"]:
            await interaction.response.send_message(
                f"{PERMISSON} ``Column`` ``{name}`` ``already exists.``", ephemeral=True
            )
            return
        if len(self.table["column_names"]) - 2 >= 20:
            await interaction.response.send_message(
                f"{PERMISSON} ``Tables are limited to 20 custom columns.``", ephemeral=True
            )
            return
        self.table["columns"] += 1
        self.table["column_names"].append(name)
        for row in self.table["data"]:
            row.append("")
        save_settings()
        await interaction.response.send_message(
            f"{CHECK} ``Column`` ``{name}`` ``created.``", ephemeral=True
        )


class TogglePingRequest(discord.ui.Button):
    def __init__(self, table: dict, ctx_or_interaction):
        enabled = table.get("ping_managers", False)
        super().__init__(
            label="Disable request pings" if enabled else "Enable request pings",
            style=discord.ButtonStyle.grey
        )
        self.table = table
        self.allowed_user = ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.allowed_user:
            await interaction.response.send_message(f"{PERMISSON} ``You did not invoke this command.``", ephemeral=True)
            return
        self.table["ping_managers"] = not self.table.get("ping_managers", False)
        save_settings()
        self.label = "Disable request pings" if self.table["ping_managers"] else "Enable request pings"
        await interaction.response.edit_message(view=self.view)


class ToggleAutoRemove(discord.ui.Button):
    def __init__(self, table: dict, ctx_or_interaction):
        enabled = table.get("auto_remove_on_role_loss", False)
        super().__init__(
            label="Disable auto-remove" if enabled else "Enable auto-remove",
            style=discord.ButtonStyle.grey
        )
        self.table = table
        self.allowed_user = ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.allowed_user:
            await interaction.response.send_message(f"{PERMISSON} ``You did not invoke this command.``", ephemeral=True)
            return
        self.table["auto_remove_on_role_loss"] = not self.table.get("auto_remove_on_role_loss", False)
        save_settings()
        self.label = "Disable auto-remove" if self.table["auto_remove_on_role_loss"] else "Enable auto-remove"
        await interaction.response.edit_message(view=self.view)


class RenameTable_Input(discord.ui.Modal, title="Rename Table"):
    new_name = discord.ui.TextInput(
        label="Enter a new name for the table",
        placeholder="Type here...",
        required=True,
        max_length=50
    )

    def __init__(self, table: dict):
        super().__init__()
        self.table = table

    async def on_submit(self, interaction: discord.Interaction):
        name = self.new_name.value.strip()
        guild_settings = config.get_guild(interaction.guild.id)

        if any(t["name"] == name for t in guild_settings["ALL_TABLES"] if t is not self.table):
            await interaction.response.send_message(
                f"{PERMISSON} ``A table named`` ``{name}`` ``already exists.``", ephemeral=True
            )
            return

        self.table["name"] = name
        save_settings()
        await interaction.response.send_message(
            f"{CHECK} ``Table renamed to`` ``{name}``.", ephemeral=True
        )


class RenameTable(discord.ui.Button):
    def __init__(self, table: dict, ctx_or_interaction):
        super().__init__(label="Rename Table", style=discord.ButtonStyle.grey)  # was: .gry (typo)
        self.table = table
        self.allowed_user = ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.allowed_user:
            await interaction.response.send_message(f"{PERMISSON} ``You did not invoke this command.``", ephemeral=True)
            return
        await interaction.response.send_modal(RenameTable_Input(self.table))


class AddColumn(discord.ui.Button):
    def __init__(self, table: dict, ctx_or_interaction):
        super().__init__(label="Add Column", style=discord.ButtonStyle.green)
        self.table = table
        self.allowed_user = ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.allowed_user:
            await interaction.response.send_message(f"{PERMISSON} ``You did not invoke this command.``", ephemeral=True)
            return
        await interaction.response.send_modal(AddColumn_Input(self.table))


class RemoveColumn_Input(discord.ui.Modal, title="Remove Column"):
    column_name = discord.ui.TextInput(
        label="Enter the name of the column",
        placeholder="Type here...",
        required=True,
        max_length=50
    )

    def __init__(self, table: dict):
        super().__init__()
        self.table = table

    async def on_submit(self, interaction: discord.Interaction):
        name = self.column_name.value

        if name in ("User", "Timestamp") and self.table["column_names"][:2] == ["User", "Timestamp"]:
            await interaction.response.send_message(
                f"{PERMISSON} ``The`` ``{name}`` ``column cannot be removed.``", ephemeral=True
            )
            return

        try:
            index = self.table["column_names"].index(name)
        except ValueError:
            await interaction.response.send_message(
                f"{PERMISSON} ``Column`` ``{name}`` ``not found.``", ephemeral=True
            )
            return

        self.table["columns"] -= 1
        self.table["column_names"].pop(index)
        for row in self.table["data"]:
            row.pop(index)
        save_settings()

        await interaction.response.send_message(
            f"{CHECK} ``Column`` ``{name}`` ``removed.``", ephemeral=True
        )


class RemoveColumn(discord.ui.Button):
    def __init__(self, table: dict, ctx_or_interaction):
        super().__init__(label="Remove Column", style=discord.ButtonStyle.red)
        self.table = table
        self.allowed_user = ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.allowed_user:
            await interaction.response.send_message(f"{PERMISSON} ``You did not invoke this command.``", ephemeral=True)
            return
        await interaction.response.send_modal(RemoveColumn_Input(self.table))


async def save_tablemember_roles(interaction, roles, table: dict):
    table["member_role_ids"] = [r.id for r in roles]
    save_settings()
    await interaction.response.send_message(
        f"{CHECK} ``Saved member roles:`` {', '.join(r.name for r in roles)}", ephemeral=True
    )


async def save_tablemanager_roles(interaction, roles, table: dict):
    table["manager_role_ids"] = [r.id for r in roles]
    save_settings()
    await interaction.response.send_message(
        f"{CHECK} ``Saved manager roles:`` {', '.join(r.name for r in roles)}", ephemeral=True
    )


async def save_tableadmin_roles(interaction, roles, table: dict):
    table["admin_role_ids"] = [r.id for r in roles]
    save_settings()
    await interaction.response.send_message(
        f"{CHECK} ``Saved admin roles:`` {', '.join(r.name for r in roles)}", ephemeral=True
    )


async def save_requestchannel_id(interaction, channels, table: dict):
    if not channels:
        return
    guild_settings = config.get_guild(interaction.guild.id)
    guild_settings["TABLE_REQUEST_CHANNEL_ID"] = channels[0].id  # was: config.TABLE_REQUEST_CHANNEL_ID
    save_settings()
    await interaction.response.send_message(
        f"{CHECK} ``Table update requests set to`` {channels[0].mention}", ephemeral=True
    )


async def save_backupchannel_id(interaction, channels, table: dict):
    if not channels:
        return
    guild_settings = config.get_guild(interaction.guild.id)
    guild_settings["TABLE_BACKUP_CHANNEL_ID"] = channels[0].id  # was: config.TABLE_BACKUP_CHANNEL_ID
    save_settings()
    await interaction.response.send_message(
        f"{CHECK} ``Table backups set to`` {channels[0].mention}", ephemeral=True
    )


class Table_Settings(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="table-settings", description="Configure the settings of a table.")
    @app_commands.autocomplete(table_name=table_name_autocomplete)
    async def table_settings(self, interaction: discord.Interaction, table_name: str):
        await self.table_settings_logic(interaction, table_name)

    @commands.command(name="table-settings")
    async def table_settings_prefix(self, ctx, table_name: str):
        await self.table_settings_logic(ctx, table_name)

    async def table_settings_logic(self, ctx_or_interaction, table_name: str):
        if not await verifyCommandPermissions(ctx_or_interaction, CommandType.SERVER_ADMIN):
            return

        guild_settings = config.get_guild(ctx_or_interaction.guild.id)
        table = next((t for t in guild_settings["ALL_TABLES"] if t["name"] == table_name), None)
        if table is None:
            msg = f"{ERROR} ``Table`` ``{table_name}`` ``not found.``"
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.response.send_message(msg, ephemeral=True)
            else:
                await ctx_or_interaction.send(msg)
            return

        embeds = [
            discord.Embed(
                title=f"Table {table_name} Settings - Rename Table",
                description="Rename this table. The new name must be unique across all tables."
            ),
            discord.Embed(
                title=f"Table {table_name} Settings - Manage Columns",
                description="Manage the columns within the table. At least one column is required."
            ),
            discord.Embed(
                title=f"Table {table_name} Settings - Manage User Roles",
                description="Select which role(s) are members of the table. Members will be able to create requests to add rows to the table, and view their roles."
            ),
            discord.Embed(
                title=f"Table {table_name} Settings - Manage Manager Roles",
                description="Select which role(s) are managers of the table. Managers can review requests and view the entire table."
            ),
            discord.Embed(
                title=f"Table {table_name} Settings - Manage Administration Roles",
                description="Select which role(s) are administrators of the table. Admins have all permissions of Managers, and can also add and remove any row in the table."
            ),
            discord.Embed(
                title=f"Table {table_name} Settings - Manage Request Channel",
                description="Select which channel table modification requests should be sent to. Table users can create requests, and managers can review them."
            ),
            discord.Embed(
                title=f"Table {table_name} Settings - Manage Request Settings",
                description="Enable or disable submitted requests pinging all roles with manager permissions for this table."
            ),
            discord.Embed(
                title=f"Table {table_name} Settings - Manage Table Backup",
                description="Select which channel should receive a backup of the table every 24 hours. If you delete a table, you can find all of its information stored in the backup, allowing it to be recreated. Leave this empty if you do not wish for it to be logged."
            ),
            discord.Embed(
                title=f"Table {table_name} Settings - Auto Remove on Role Loss",
                description="When enabled, if a user no longer has any of the member roles required to make row requests, their row is automatically removed from the table."
            ),
        ]

        view = PageView(
            embeds=embeds,
            ctx_or_interaction=ctx_or_interaction,
            page_menus={
                0: [lambda: RenameTable(table, ctx_or_interaction)],
                1: [lambda: AddColumn(table, ctx_or_interaction), lambda: RemoveColumn(table, ctx_or_interaction)],
                2: [lambda: SelectRoles_Menu(lambda i, r: save_tablemember_roles(i, r, table), ctx_or_interaction)],
                3: [lambda: SelectRoles_Menu(lambda i, r: save_tablemanager_roles(i, r, table), ctx_or_interaction)],
                4: [lambda: SelectRoles_Menu(lambda i, r: save_tableadmin_roles(i, r, table), ctx_or_interaction)],
                5: [lambda: SelectChannels_Menu(lambda i, c: save_requestchannel_id(i, c, table), ctx_or_interaction)],
                6: [lambda: TogglePingRequest(table, ctx_or_interaction)],
                7: [lambda: SelectChannels_Menu(lambda i, c: save_backupchannel_id(i, c, table), ctx_or_interaction)],
                8: [lambda: ToggleAutoRemove(table, ctx_or_interaction)],
            }
        )

        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.response.send_message(embed=embeds[0], view=view)
        else:
            await ctx_or_interaction.send(embed=embeds[0], view=view)


async def setup(bot):
    await bot.add_cog(Table_Settings(bot))