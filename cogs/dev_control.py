import discord
import io
import os
import sys
from discord.ext import commands
from config import CHECK, ERROR

OWNER_ID = 1057431766568284360
ROLE_ID_TO_ADD = 1327919872843452426


class Dev_Control(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="kill")
    async def dev_kill(self, ctx):
        if ctx.author.id != OWNER_ID:
            return
        await ctx.message.delete()
        await ctx.send(f"{CHECK} ``Shutting down``")
        await self.bot.close()

    @commands.command(name="restart")
    async def dev_restart(self, ctx):
        if ctx.author.id != OWNER_ID:
            return
        await ctx.message.delete()
        await ctx.send(f"{CHECK} ``Restarting``")
        os.execv(sys.executable, [sys.executable] + sys.argv)

    @commands.command(name="errors")
    async def dev_errors(self, ctx):
        if ctx.author.id != OWNER_ID:
            return
        await ctx.message.delete()
        try:
            with open("bot.log", "rb") as f:
                await ctx.send(file=discord.File(f, filename="errors.txt"))
        except FileNotFoundError:
            await ctx.send("No log file found.")

    @commands.command(name="clear-errors")
    async def dev_clear_errors(self, ctx):
        if ctx.author.id != OWNER_ID:
            return
        await ctx.message.delete()
        try:
            open("bot.log", "w").close()
            await ctx.send("Log cleared.")
        except FileNotFoundError:
            await ctx.send("No log file found.")

    @commands.command(name="say")
    async def dev_say(self, ctx, *, message: str):
        if ctx.author.id != OWNER_ID:
            return
        await ctx.message.delete()
        await ctx.send(message)

    @commands.command(name="key")
    async def dev_key(self, ctx, member: discord.Member):
        if ctx.author.id != OWNER_ID:
            return
        await ctx.message.delete()
        role = ctx.guild.get_role(ROLE_ID_TO_ADD)
        if role is None:
            await ctx.send(f"{ERROR} ``Role not found.``")
            return

        if role in member.roles:
            await member.remove_roles(role)
            await ctx.send(f"{CHECK} ``Removed Key from`` {member.mention}")
        else:
            await member.add_roles(role)
            await ctx.send(f"{CHECK} ``Added Key to`` {member.mention}")


async def setup(bot):
    await bot.add_cog(Dev_Control(bot))