import discord
import aiohttp
import os
from discord.ext import commands
from config import CHECK, ERROR

OWNER_ID = 1057431766568284360


class Dev_GroupFunds(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="groupfunds")
    async def dev_group_funds(self, ctx, group_id: int):
        if ctx.author.id != OWNER_ID:
            return

        await ctx.message.delete()

        cookie = os.getenv("ROBLOSECURITY")
        headers = {"Cookie": f".ROBLOSECURITY={cookie}"} if cookie else {}

        async with aiohttp.ClientSession() as session:
            # Fetch group info (public)
            async with session.get(
                f"https://groups.roblox.com/v1/groups/{group_id}"
            ) as resp:
                if resp.status != 200:
                    await ctx.send(f"{ERROR} ``Could not fetch group {group_id} (status {resp.status}).``")
                    return
                group_data = await resp.json()

            # Fetch group funds (requires auth)
            current_funds = None
            pending_funds = None
            if cookie:
                async with session.get(
                    f"https://economy.roblox.com/v1/groups/{group_id}/currency",
                    headers=headers,
                ) as resp:
                    if resp.status == 200:
                        funds_data = await resp.json()
                        current_funds = funds_data.get("robux")
                async with session.get(
                    f"https://economy.roblox.com/v1/groups/{group_id}/revenue/summary/daily",
                    headers=headers,
                ) as resp:
                    if resp.status == 200:
                        summary = await resp.json()
                        pending_funds = summary.get("pendingRobux")

        group_name = group_data.get("name", f"Group {group_id}")
        group_url = f"https://www.roblox.com/communities/{group_id}"

        def fmt(val):
            if val is None:
                return "N/A"
            return f"R$ {val:,}"

        total = None
        if current_funds is not None and pending_funds is not None:
            total = current_funds + pending_funds

        embed = discord.Embed(
            title=group_name,
            url=group_url,
            color=discord.Color.blurple(),
        )
        embed.add_field(name="Current Funds", value=fmt(current_funds), inline=True)
        embed.add_field(name="Pending Funds", value=fmt(pending_funds), inline=True)
        embed.add_field(name="Total Funds", value=fmt(total), inline=True)
        embed.set_footer(text=f"Group ID: {group_id}")

        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Dev_GroupFunds(bot))
