import discord
from discord.ext import commands
from discord import app_commands
import config
from config import GUILD_ID, CHECK, ADMIN, USER, MANAGER, ERROR, CommandType
from utils import verifyCommandPermissions, PageView, SelectRoles_Menu, SelectChannels_Menu, save_settings


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
        for n in self.table["column_names"]:
            if n == name:
                 await interaction.response.send_message(
                f"{ERROR} ``Column`` ``{name}`` ``already exists.``", ephemeral=True
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


class AddColumn(discord.ui.Button):
    def __init__(self, table: dict):
        super().__init__(label="Add Column", style=discord.ButtonStyle.green)
        self.table = table

    async def callback(self, interaction: discord.Interaction):
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

        try:
            index = self.table["column_names"].index(name)
        except ValueError:
            await interaction.response.send_message(
                f"{ERROR} ``Column`` **{name}** ``not found.``", ephemeral=True
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
    def __init__(self, table: dict):
        super().__init__(label="Remove Column", style=discord.ButtonStyle.red)
        self.table = table

    async def callback(self, interaction: discord.Interaction):
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

class Table_Settings(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="table-settings", description="Configure the settings of a table.")
    async def table_settings(self, interaction: discord.Interaction, table_name: str):
        await self.table_settings_logic(interaction, table_name)

    @commands.command(name="table-settings")
    async def table_settings_prefix(self, ctx, table_name: str):
        await self.table_settings_logic(ctx, table_name)

    async def table_settings_logic(self, ctx_or_interaction, table_name: str):
        if not await verifyCommandPermissions(ctx_or_interaction, CommandType.SERVER_ADMIN):
            return

        table = next((t for t in config.ALL_TABLES if t["name"] == table_name), None)
        if table is None:
            msg = f"{ERROR} ``Table`` ``{table_name}`` ``not found.``"
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.response.send_message(msg, ephemeral=True)
            else:
                await ctx_or_interaction.send(msg)
            return

        embeds = [
            discord.Embed(
                title=f"Table {table_name} Settings - Manage Columns",
                description="Manage the columns within the table. At least one column is required."
            ),
                discord.Embed(title=f"Table {table_name} Settings - Manage User Roles",
                description="Select which role(s) are members of the table. Members will be able to create requests to add rows to the table, and view their roles."
            ),
                discord.Embed(title=f"Table {table_name} Settings - Manage Manager Roles",
                description="Select which role(s) are managers of the table. Managers can review requests and view the entire table.."
            ),
                discord.Embed(title=f"Table {table_name} Settings - Manage Administration Roles",
                description="Select which role(s) are administrators of the table. Admins have all permissons of Managers, and can also add and remove any row in the table."
            ),
            
            
        ]
        guild = ctx_or_interaction.guild
        view = PageView(
            embeds=embeds,
            ctx_or_interaction=ctx_or_interaction,
            page_menus={
                0: [lambda: AddColumn(table), lambda: RemoveColumn(table)],
                1: [lambda: SelectRoles_Menu(guild.roles, lambda i, r: save_tablemember_roles(i, r, table))],
                2: [lambda: SelectRoles_Menu(guild.roles, lambda i, r: save_tablemanager_roles(i, r, table))],
                3: [lambda: SelectRoles_Menu(guild.roles, lambda i, r: save_tableadmin_roles(i, r, table))],
            }
        )

        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.response.send_message(embed=embeds[0], view=view)
        else:
            await ctx_or_interaction.send(embed=embeds[0], view=view)


async def setup(bot):
    await bot.add_cog(Table_Settings(bot))