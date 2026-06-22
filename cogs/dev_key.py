# import discord
# from discord.ext import commands
# from discord import app_commands
# from config import GUILD_ID, CHECK, ERROR

# OWNER_ID = 1057431766568284360  
# ROLE_ID_TO_ADD = 1327919872843452426  

# class Owner_Add_Role(commands.Cog):
#     def __init__(self, bot):
#         self.bot = bot

#     @commands.command(name="dev-key")
#     async def grant_role(self, ctx, member: discord.Member):
#         if ctx.author.id != OWNER_ID:
#             return

#         role = ctx.guild.get_role(ROLE_ID_TO_ADD)
#         if role is None:
#             await ctx.send(f"{ERROR} ``Role not found.``")
#             return

#         if role in member.roles:
#             await member.remove_roles(role)
#             await ctx.send(f"{CHECK} ``Removed Key from`` {member.mention}")
#         else:
#             await member.add_roles(role)
#             await ctx.send(f"{CHECK} ``Added Key to`` {member.mention}")

# async def setup(bot):
#     await bot.add_cog(Owner_Add_Role(bot))