import discord
import io
import os
import sys
import json
import subprocess
from discord.ext import commands
from config import CHECK, ERROR
import config

OWNER_ID = 1057431766568284360
ROLE_ID_TO_ADD = 1327919872843452426

SETTINGS_FILE = "settings.json"

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

    @commands.command(name="commands")
    async def dev_commands(self, ctx):
        if ctx.author.id != OWNER_ID:
            return

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
        if ctx.author.id != OWNER_ID:
            return
        await ctx.message.delete()

        fetch = subprocess.run(["git", "fetch", "origin", "main"], capture_output=True, text=True)
        reset = subprocess.run(["git", "reset", "--hard", "origin/main"], capture_output=True, text=True)

        output = (fetch.stdout + fetch.stderr + reset.stdout + reset.stderr).strip() or "No output."
        embed = discord.Embed(title="Git Update")
        embed.add_field(name="Output", value=f"```{output}```", inline=False)
        await ctx.send(embed=embed)

        if fetch.returncode == 0 and reset.returncode == 0:
            await ctx.send(f"{CHECK} ``Restarting``")
            os.execv(sys.executable, [sys.executable] + sys.argv)
        else:
            await ctx.send(f"{ERROR} ``Update failed, not restarting.``")

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

    @commands.command(name="servers")
    async def dev_servers(self, ctx):
        if ctx.author.id != OWNER_ID:
            return

        guilds = sorted(self.bot.guilds, key=lambda g: g.member_count, reverse=True)
        lines = [f"`{g.name}` — {g.member_count} members — owner: <@{g.owner_id}>" for g in guilds]
        embed = discord.Embed(title=f"Servers ({len(guilds)})", description="\n".join(lines))
        await ctx.send(embed=embed)

    @commands.command(name="cat")
    async def dev_cat(self, ctx, path: str):
        if ctx.author.id != OWNER_ID:
            return

        if os.path.isabs(path) or ".." in path.replace("\\", "/").split("/"):
            await ctx.send("``Refusing to read paths outside the bot's directory.``")
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

        if size < 1900:
            await ctx.send(f"```py\n{content}\n```")
            return

        buffer = io.BytesIO(content.encode("utf-8"))
        await ctx.send(
            f"``File is {size} bytes, sending as an attachment instead of inline:``",
            file=discord.File(buffer, filename=os.path.basename(path))
        )

    @commands.command(name="ls")
    async def dev_ls(self, ctx, path: str = "."):
        if ctx.author.id != OWNER_ID:
            return

        if os.path.isabs(path) or ".." in path.replace("\\", "/").split("/"):
            await ctx.send("``Refusing to list paths outside the bot's directory.``")
            return

        if not os.path.exists(path):
            await ctx.send(f"``Path not found:`` ``{path}``")
            return

        entries = sorted(os.listdir(path))
        if not entries:
            await ctx.send(f"``{path}`` ``is empty.``")
            return

        lines = [f"{e}/" if os.path.isdir(os.path.join(path, e)) else e for e in entries]
        await ctx.send(f"``Contents of`` ``{path}``:\n```\n{chr(10).join(lines)}\n```")

    @commands.command(name="restore-settings")
    async def dev_restore_settings(self, ctx, target_guild_id: int = None):
        if ctx.author.id != OWNER_ID:
            return

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

        guild_id = target_guild_id or ctx.guild.id

        if looks_like_wrapped_format(uploaded_data):
            new_entries = uploaded_data
            table_counts = {gid: len(g.get("ALL_TABLES", [])) for gid, g in new_entries.items()}
        elif looks_like_flat_format(uploaded_data):
            new_entries = {str(guild_id): uploaded_data}
            table_counts = {str(guild_id): len(uploaded_data.get("ALL_TABLES", []))}
        else:
            await ctx.send(f"{ERROR} ``Uploaded file doesn't look like a recognized settings format. Nothing was changed.``")
            return

        try:
            with open(SETTINGS_FILE, "r") as f:
                on_disk = json.load(f)
            if not isinstance(on_disk, dict):
                on_disk = {}
        except (FileNotFoundError, json.JSONDecodeError):
            on_disk = {}

        if looks_like_flat_format(on_disk) and not looks_like_wrapped_format(on_disk):
            on_disk = {}

        on_disk.update(new_entries)

        with open(SETTINGS_FILE, "w") as f:
            json.dump(on_disk, f, indent=4)

        from config import CommandType
        for gid_str, gdata in new_entries.items():
            gid = int(gid_str)
            settings = config.get_guild(gid)
            settings["TABLE_REQUEST_CHANNEL_ID"] = gdata.get("TABLE_REQUEST_CHANNEL_ID", 0)
            settings["TABLE_BACKUP_CHANNEL_ID"]  = gdata.get("TABLE_BACKUP_CHANNEL_ID", 0)
            settings["SERVER_ADMIN_ROLE_IDS"]    = gdata.get("SERVER_ADMIN_ROLE_IDS", [])
            settings["ADMIN_ROLE_IDS"]           = gdata.get("ADMIN_ROLE_IDS", [])
            settings["MANAGER_ROLE_IDS"]         = gdata.get("MANAGER_ROLE_IDS", [])
            settings["MEMBER_ROLE_IDS"]          = gdata.get("MEMBER_ROLE_IDS", [])
            settings["LOG_UNSUCCESSFUL"]         = gdata.get("LOG_UNSUCCESSFUL", True)
            settings["LOG_CHANNELS"][CommandType.USER]    = gdata.get("USER_LOG_CHANNEL", 0)
            settings["LOG_CHANNELS"][CommandType.MANAGER] = gdata.get("MANAGER_LOG_CHANNEL", 0)
            settings["LOG_CHANNELS"][CommandType.ADMIN]   = gdata.get("ADMIN_LOG_CHANNEL", 0)
            settings["ALL_TABLES"]               = gdata.get("ALL_TABLES", [])
            settings["COMMAND_PREFIX"]           = gdata.get("COMMAND_PREFIX", "t! ")

        summary = "\n".join(f"- Guild `{gid}`: {count} table(s)" for gid, count in table_counts.items())
        await ctx.send(f"{CHECK} ``Settings restored and reloaded into memory.``\n{summary}")


async def setup(bot):
    await bot.add_cog(Dev_Control(bot))
