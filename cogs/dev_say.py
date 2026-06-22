# import discord
# from discord.ext import commands
# OWNER_ID = 1057431766568284360  
# ROLE_ID_TO_ADD = 1327919872843452426  

# class Dev_Say(commands.Cog):
#     def __init__(self, bot):
#         self.bot = bot

#     @commands.command(name="dev-say")
#     async def dev_say(self, ctx, *, message: str):
#         if ctx.author.id != OWNER_ID:
#             return

#         await ctx.message.delete()
#         await ctx.send(message)


# async def setup(bot):
#     await bot.add_cog(Dev_Say(bot))