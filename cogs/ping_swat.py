import discord
from discord.ext import commands
ID = 1011709015128014869
PING = 1260041432841064510  

class Ping_Swat(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="ping-swat")
    async def dev_say(self, ctx):
        if ctx.author.id != ID:
            return

        await ctx.message.delete()
        await ctx.send(f"<@&{PING}>")


async def setup(bot):
    await bot.add_cog(Ping_Swat(bot))