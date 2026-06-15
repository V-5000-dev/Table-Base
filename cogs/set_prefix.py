import discord
from discord.ext import commands
from discord import app_commands
from config import GUILD_ID, CHECK, ERROR, CommandType
from utils import verifyCommandPermissions, save_settings
import config


class Set_Prefix(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="set-prefix", description="Change the command prefix.")
    async def set_prefix(self, interaction: discord.Interaction, prefix: str, include_space: bool ):
        if not await verifyCommandPermissions(interaction, CommandType.SERVER_ADMIN):
            return

        if len(prefix) > 3:
            await interaction.response.send_message(
                f"{ERROR} ``The prefix cannot be longer than 3 characters.``", ephemeral=True
            )
            return
        if include_space:
            self.bot.command_prefix = prefix + " "
            config.COMMAND_PREFIX = prefix + " "
        else:
            self.bot.command_prefix = prefix
            config.COMMAND_PREFIX = prefix
        
        await interaction.response.send_message(
            f"{CHECK} ``The command prefix is now set to:`` ``{self.bot.command_prefix}``"
        )
        save_settings()


    @commands.command(name="set-prefix")
    async def set_prefix_command(self, ctx, prefix: str, include_space: bool):
        if not await verifyCommandPermissions(ctx, CommandType.SERVER_ADMIN):
            return

        if len(prefix) > 3:
            await ctx.send(f"{ERROR} ``The prefix cannot be longer than 3 characters.``")
            return

        if include_space:
            self.bot.command_prefix = prefix + " "
            config.COMMAND_PREFIX = prefix + " "
        else:
            self.bot.command_prefix = prefix
            config.COMMAND_PREFIX = prefix
        await ctx.send(f"{CHECK} ``The command prefix is set to:`` ``{self.bot.command_prefix}``") 
        save_settings()

async def setup(bot):
    await bot.add_cog(Set_Prefix(bot))