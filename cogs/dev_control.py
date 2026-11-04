import discord
import io
import logging
import math
import os
import sys
import json
import time
import asyncio
import subprocess
from discord.ext import commands, tasks
from config import CHECK, ERROR
import config
from utils import apply_guild_data, save_settings

OWNER_ID = 1057431766568284360
ROLE_ID_TO_ADD = 1327919872843452426

GIT_TIMEOUT_SECONDS = 60
MESSAGE_TEXT_LIMIT = 1900

FLAT_FORMAT_KEYS = {
    "TABLE_REQUEST_CHANNEL_ID",
    "TABLE_BACKUP_CHANNEL_ID",
    "SERVER_ADMIN_ROLE_IDS",
    "ADMIN_ROLE_IDS",
    "MANAGER_ROLE_IDS",
    "MEMBER_ROLE_IDS",
    "LOG_UNSUCCESSFUL",
    "USER_LOG_CHANNEL",
    "MANAGER_LOG_CHANNEL",
    "ADMIN_LOG_CHANNEL",
    "ALL_TABLES",
    "COMMAND_PREFIX",
}


def looks_like_flat_format(data: dict) -> bool:
    if not isinstance(data, dict):
        return False
    return len(FLAT_FORMAT_KEYS & set(data.keys())) >= 5


def looks_like_wrapped_format(data: dict) -> bool:
    if not isinstance(data, dict) or not data:
        return False
    return all(isinstance(k, str) and k.isdigit() and isinstance(v, dict) for k, v in data.items())


def is_secret_file(path: str) -> bool:
    return ".env" in os.path.basename(path).lower()


async def run_git(*args: str) -> subprocess.CompletedProcess:
    """Run git in a thread, so that a slow command cannot freeze the bot."""
    try:
        return await asyncio.to_thread(
            subprocess.run, ["git", *args], capture_output=True, text=True, timeout=GIT_TIMEOUT_SECONDS
        )
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(
            ["git", *args], 1, "", f"git {args[0]} timed out after {GIT_TIMEOUT_SECONDS}s"
        )


async def update_to(branch: str) -> tuple[bool, str]:
    """Fetch a branch and reset to it. The reset only runs if the fetch worked."""
    fetch = await run_git("fetch", "origin", branch)
    output = fetch.stdout + fetch.stderr
    if fetch.returncode != 0:
        return False, output.strip() or "No output."

    reset = await run_git("reset", "--hard", f"origin/{branch}")
    output += reset.stdout + reset.stderr
    return reset.returncode == 0, output.strip() or "No output."


async def delete_invocation(ctx):
    """Delete the command message if possible. Failing must not stop the command."""
    try:
        await ctx.message.delete()
    except discord.HTTPException:
        pass


class Dev_Control(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        self.expire_keys.start()

    async def cog_unload(self):
        self.expire_keys.cancel()

    async def cog_check(self, ctx):
        return ctx.author.id == OWNER_ID

    @tasks.loop(minutes=1)
    async def expire_keys(self):
        now = time.time()
        for guild_id, guild_settings in list(config.GUILD_SETTINGS.items()):
            for user_id, entry in list(guild_settings.get("KEY_EXPIRIES", {}).items()):
                if entry["expires_at"] <= now:
                    await self.remove_expired_key(guild_id, guild_settings, user_id, entry)

    @expire_keys.before_loop
    async def before_expire_keys(self):
        await self.bot.wait_until_ready()

    async def remove_expired_key(self, guild_id: int, guild_settings: dict, user_id: str, entry: dict):
        guild = self.bot.get_guild(guild_id)
        role = guild.get_role(ROLE_ID_TO_ADD) if guild else None

        if role is not None:
            try:
                member = await guild.fetch_member(int(user_id))
                await member.remove_roles(role)
            except discord.NotFound:
                pass
            except discord.HTTPException:
                # The entry stays, so this is tried again on the next loop.
                logging.exception(f"Could not remove Key from {user_id} in guild {guild_id}")
                return

        del guild_settings["KEY_EXPIRIES"][user_id]
        save_settings()

        channel = self.bot.get_channel(entry["channel_id"])
        if channel is not None:
            try:
                await channel.send(f"{CHECK} ``Key auto-removed from`` <@{user_id}>")
            except discord.HTTPException:
                pass

    @commands.command(name="kill")
    async def dev_kill(self, ctx):
        await delete_invocation(ctx)
        await ctx.send(f"{CHECK} ``Shutting down``")
        await self.bot.close()

    @commands.command(name="commands")
    async def dev_commands(self, ctx):
        prefix_commands = sorted(c.name for c in self.bot.commands)
        slash_commands = sorted(c.name for c in self.bot.tree.get_commands())

        embed = discord.Embed(title="Loaded Commands")
        embed.add_field(
            name="Prefix Commands",
            value="\n".join(f"`{c}`" for c in prefix_commands) or "None",
            inline=True
        )
        embed.add_field(
            name="Slash Commands",
            value="\n".join(f"`/{c}`" for c in slash_commands) or "None",
            inline=True
        )
        await ctx.send(embed=embed)

    @commands.command(name="update")
    async def dev_update(self, ctx):
        await delete_invocation(ctx)

        updated, output = await update_to("main")

        embed = discord.Embed(title="Git Update")
        embed.add_field(name="Output", value=f"```{output[:1000]}```", inline=False)
        await ctx.send(embed=embed)

        if updated:
            await ctx.send(f"{CHECK} ``Restarting``")
            os.execv(sys.executable, [sys.executable] + sys.argv)
        else:
            await ctx.send(f"{ERROR} ``Update failed, not restarting.``")

    @commands.command(name="push")
    async def dev_push(self, ctx, *, message: str):
        await delete_invocation(ctx)

        branch = (await run_git("branch", "--show-current")).stdout.strip() or "main"
        add = await run_git("add", ".")
        commit = await run_git("commit", "-m", message)
        push = await run_git("push", "origin", branch)

        output = (add.stdout + add.stderr + commit.stdout + commit.stderr + push.stdout + push.stderr).strip() or "No output."
        embed = discord.Embed(title="Git Commit & Push")
        embed.add_field(name="Output", value=f"```{output[:1000]}```", inline=False)

        if commit.returncode == 0 and push.returncode == 0:
            await ctx.send(f"{CHECK} ``Committed and pushed.``", embed=embed)
        elif commit.returncode != 0:
            await ctx.send(f"{ERROR} ``Commit failed.``", embed=embed)
        else:
            await ctx.send(f"{ERROR} ``Push failed.``", embed=embed)

    @commands.command(name="pushupdate")
    async def dev_pushupdate(self, ctx):
        await delete_invocation(ctx)

        branch = (await run_git("branch", "--show-current")).stdout.strip() or "main"
        push = await run_git("push", "origin", branch)
        push_output = (push.stdout + push.stderr).strip() or "No output."
        embed = discord.Embed(title=f"Push + Update → {branch}")
        embed.add_field(name="Push Output", value=f"```{push_output[:1000]}```", inline=False)

        if push.returncode != 0:
            await ctx.send(f"{ERROR} ``Push failed, aborting update.``", embed=embed)
            return

        updated, update_output = await update_to(branch)
        embed.add_field(name="Update Output", value=f"```{update_output[:1000]}```", inline=False)

        if updated:
            await ctx.send(f"{CHECK} ``Push successful. Restarting...``", embed=embed)
            os.execv(sys.executable, [sys.executable] + sys.argv)
        else:
            await ctx.send(f"{ERROR} ``Push successful, but the update failed. Not restarting.``", embed=embed)

    @commands.command(name="restart")
    async def dev_restart(self, ctx):
        await delete_invocation(ctx)
        await ctx.send(f"{CHECK} ``Restarting``")
        os.execv(sys.executable, [sys.executable] + sys.argv)

    @commands.command(name="errors")
    async def dev_errors(self, ctx):
        await delete_invocation(ctx)
        try:
            with open("bot.log", "rb") as f:
                await ctx.send(file=discord.File(f, filename="errors.txt"))
        except FileNotFoundError:
            await ctx.send("No log file found.")
        except discord.HTTPException:
            await ctx.send(f"{ERROR} ``Could not send the log file. It may be too large.``")

    @commands.command(name="clear-errors")
    async def dev_clear_errors(self, ctx):
        await delete_invocation(ctx)
        open("bot.log", "w").close()
        await ctx.send("Log cleared.")

    @commands.command(name="say")
    async def dev_say(self, ctx, message: str):
        await delete_invocation(ctx)
        await ctx.send(message)

    @commands.command(name="key")
    async def dev_key(self, ctx, member: discord.Member, hours: float = None):
        await delete_invocation(ctx)

        if hours is not None and (hours <= 0 or not math.isfinite(hours)):
            await ctx.send(f"{ERROR} ``Hours must be a positive number.``")
            return

        role = ctx.guild.get_role(ROLE_ID_TO_ADD)
        if role is None:
            await ctx.send(f"{ERROR} ``Role not found.``")
            return

        # Without the members intent, a cached member's roles can be out of date.
        member = await ctx.guild.fetch_member(member.id)
        expiries = config.get_guild(ctx.guild.id)["KEY_EXPIRIES"]

        if role in member.roles and hours is None:
            await member.remove_roles(role)
            expiries.pop(str(member.id), None)
            save_settings()
            await ctx.send(f"{CHECK} ``Removed Key from`` {member.mention}")
            return

        await member.add_roles(role)

        if hours is None:
            expiries.pop(str(member.id), None)
            save_settings()
            await ctx.send(f"{CHECK} ``Added Key to`` {member.mention}")
            return

        expiries[str(member.id)] = {"expires_at": time.time() + hours * 3600, "channel_id": ctx.channel.id}
        save_settings()
        await ctx.send(f"{CHECK} ``Added Key to`` {member.mention} ``— auto-removes in {hours:g}h``")

    @commands.command(name="servers")
    async def dev_servers(self, ctx):
        guilds = sorted(self.bot.guilds, key=lambda g: g.member_count or 0, reverse=True)
        lines = [f"`{g.name}` — {g.member_count} members — owner: <@{g.owner_id}>" for g in guilds]
        embed = discord.Embed(title=f"Servers ({len(guilds)})", description="\n".join(lines)[:4000])
        await ctx.send(embed=embed)

    @commands.command(name="cat")
    async def dev_cat(self, ctx, path: str):
        if os.path.isabs(path) or ".." in path.replace("\\", "/").split("/"):
            await ctx.send("``Refusing to read paths outside the bot's directory.``")
            return

        if is_secret_file(path):
            await ctx.send("``Refusing to post a secrets file in chat.``")
            return

        if not os.path.exists(path):
            await ctx.send(f"``File not found:`` ``{path}``\n``Current working directory:`` ``{os.getcwd()}``")
            return

        if not os.path.isfile(path):
            await ctx.send(f"``That's a directory, not a file:`` ``{path}``")
            return

        size = os.path.getsize(path)
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        if size < MESSAGE_TEXT_LIMIT:
            await ctx.send(f"```py\n{content}\n```")
            return

        buffer = io.BytesIO(content.encode("utf-8"))
        await ctx.send(
            f"``File is {size} bytes, sending as an attachment instead of inline:``",
            file=discord.File(buffer, filename=os.path.basename(path))
        )

    @commands.command(name="ls")
    async def dev_ls(self, ctx, path: str = "."):
        if os.path.isabs(path) or ".." in path.replace("\\", "/").split("/"):
            await ctx.send("``Refusing to list paths outside the bot's directory.``")
            return

        if not os.path.exists(path):
            await ctx.send(f"``Path not found:`` ``{path}``")
            return

        if not os.path.isdir(path):
            await ctx.send(f"``That's a file, not a directory:`` ``{path}``")
            return

        entries = sorted(os.listdir(path))
        if not entries:
            await ctx.send(f"``{path}`` ``is empty.``")
            return

        lines = [f"{e}/" if os.path.isdir(os.path.join(path, e)) else e for e in entries]
        listing = "\n".join(lines)

        if len(listing) < MESSAGE_TEXT_LIMIT:
            await ctx.send(f"``Contents of`` ``{path}``:\n```\n{listing}\n```")
            return

        await ctx.send(
            f"``Contents of`` ``{path}``:",
            file=discord.File(io.BytesIO(listing.encode("utf-8")), filename="listing.txt")
        )


    @commands.command(name="restore-settings")
    #(Coded with Claude)
    async def dev_restore_settings(self, ctx, target_guild_id: int = None):
        if not ctx.message.attachments:
            await ctx.send(f"{ERROR} ``Attach a settings_export.json file to this command.``")
            return

        attachment = ctx.message.attachments[0]
        if not attachment.filename.lower().endswith(".json"):
            await ctx.send(f"{ERROR} ``Attachment must be a .json file.``")
            return

        raw = await attachment.read()
        try:
            uploaded_data = json.loads(raw.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            await ctx.send(f"{ERROR} ``Could not parse the uploaded file as JSON:`` ``{e}``")
            return

        if looks_like_wrapped_format(uploaded_data):
            if target_guild_id is None:
                new_entries = uploaded_data
            elif len(uploaded_data) == 1:
                new_entries = {str(target_guild_id): next(iter(uploaded_data.values()))}
            else:
                await ctx.send(
                    f"{ERROR} ``This file holds {len(uploaded_data)} guilds, so it cannot be restored "
                    f"to one target guild. Nothing was changed.``"
                )
                return
        elif looks_like_flat_format(uploaded_data):
            guild_id = target_guild_id or (ctx.guild.id if ctx.guild else None)
            if guild_id is None:
                await ctx.send(f"{ERROR} ``Give a target guild ID when restoring this file from a DM.``")
                return
            new_entries = {str(guild_id): uploaded_data}
        else:
            await ctx.send(f"{ERROR} ``Uploaded file doesn't look like a recognized settings format. Nothing was changed.``")
            return

        for gid_str, gdata in new_entries.items():
            apply_guild_data(config.get_guild(int(gid_str)), gdata)
        save_settings()

        summary = "\n".join(
            f"- Guild `{gid}`: {len(g.get('ALL_TABLES', []))} table(s)" for gid, g in new_entries.items()
        )
        await ctx.send(f"{CHECK} ``Settings restored and reloaded into memory.``\n{summary}")


async def setup(bot):
    await bot.add_cog(Dev_Control(bot))
