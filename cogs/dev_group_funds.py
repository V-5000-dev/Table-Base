import discord
import aiohttp
import asyncio
import os
from datetime import datetime, timezone
from discord.ext import commands
from config import CHECK, ERROR

OWNER_ID = 1057431766568284360


class Dev_GroupFunds(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # tracks active live embeds: message -> (group_id, group_name, task)
        self._live = {}

    async def _fetch_funds(self, session: aiohttp.ClientSession, group_id: int, cookie):
        headers = {"Cookie": f".ROBLOSECURITY={cookie}"} if cookie else {}

        async with session.get(f"https://groups.roblox.com/v1/groups/{group_id}") as resp:
            if resp.status != 200:
                body = await resp.text()
                raise ValueError(f"groups API {resp.status}: {body[:200]}")
            group_data = await resp.json()

        group_name = group_data.get("name", f"Group {group_id}")
        current_funds = None
        pending_funds = None

        if cookie:
            async with session.get(
                f"https://economy.roblox.com/v1/groups/{group_id}/currency",
                headers=headers,
            ) as resp:
                if resp.status == 200:
                    current_funds = (await resp.json()).get("robux")

            async with session.get(
                f"https://economy.roblox.com/v1/groups/{group_id}/revenue/summary/daily",
                headers=headers,
            ) as resp:
                if resp.status == 200:
                    pending_funds = (await resp.json()).get("pendingRobux")

        total = (current_funds + pending_funds) if (current_funds is not None and pending_funds is not None) else None
        return group_name, current_funds, pending_funds, total

    def _build_embed(self, group_id: int, group_name: str, current_funds, pending_funds, total) -> discord.Embed:
        def fmt(val):
            return "N/A" if val is None else f"R$ {val:,}"

        now = datetime.now(timezone.utc)
        ts = discord.utils.format_dt(now, style="T")

        embed = discord.Embed(
            title=group_name,
            url=f"https://www.roblox.com/communities/{group_id}",
            color=discord.Color.blurple(),
        )
        embed.add_field(name="Current Funds", value=fmt(current_funds), inline=True)
        embed.add_field(name="Pending Funds", value=fmt(pending_funds), inline=True)
        embed.add_field(name="Total Funds", value=fmt(total), inline=True)
        embed.set_footer(text=f"Group ID: {group_id}  •  Last updated {ts}")
        return embed

    async def _live_loop(self, message: discord.Message, group_id: int, cookie):
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            while True:
                await asyncio.sleep(60)
                try:
                    group_name, current_funds, pending_funds, total = await self._fetch_funds(session, group_id, cookie)
                    if group_name is None:
                        continue
                    embed = self._build_embed(group_id, group_name, current_funds, pending_funds, total)
                    await message.edit(embed=embed)
                except (discord.NotFound, discord.Forbidden):
                    break
                except Exception as e:
                    print(f"[groupfunds] live loop error: {e}")

    @commands.command(name="groupfunds")
    async def dev_group_funds(self, ctx, group_id: int):
        print(f"[dev_group_funds] invoked by {ctx.author.id} in guild {ctx.guild.id if ctx.guild else 'DM'}")
        if ctx.guild is None or ctx.guild.id != 1324223207536070697:
            print("[dev_group_funds] blocked: wrong guild")
            return
        if ctx.author.id != OWNER_ID:
            print("[dev_group_funds] blocked: not owner")
            return

        cookie = os.getenv("ROBLOSECURITY")
        print(f"[dev_group_funds] cookie set: {bool(cookie)}, group_id: {group_id}")

        try:
            print("[dev_group_funds] starting fetch")
            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                group_name, current_funds, pending_funds, total = await self._fetch_funds(session, group_id, cookie)
            print(f"[dev_group_funds] fetch done: {group_name}, {current_funds}, {pending_funds}")
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            print(f"[dev_group_funds] exception: {tb}")
            await ctx.send(f"{ERROR} ``Fetch error: {type(e).__name__}: {e}``")
            return

        if group_name is None:
            await ctx.send(f"{ERROR} ``Could not fetch group {group_id} — check the group ID or API availability.``")
            return

        print("[dev_group_funds] sending embed")
        await ctx.message.delete()
        embed = self._build_embed(group_id, group_name, current_funds, pending_funds, total)
        message = await ctx.send(embed=embed)

        old_task = self._live.get(message.id)
        if old_task:
            old_task.cancel()

        task = asyncio.create_task(self._live_loop(message, group_id, cookie))
        self._live[message.id] = task

    def cog_unload(self):
        for task in self._live.values():
            task.cancel()


async def setup(bot):
    await bot.add_cog(Dev_GroupFunds(bot))
    print("[dev_group_funds] cog loaded")
