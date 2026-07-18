import discord
import io
import os
from discord.ext import commands

OWNER_ID = 1057431766568284360


class Dev_Cat_File(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="dev-cat")
    async def dev_cat(self, ctx, path: str):
        """
        Owner-only. Posts the contents of a file on the bot's host back
        to Discord, so you can inspect files without remote/file access
        to the second hosting computer.

        Usage: t! dev-cat main.py
               t! dev-cat cogs/table_delete.py
        """
        if ctx.author.id != OWNER_ID:
            return

        # Basic guardrails: stay within the bot's own working directory,
        # don't allow escaping with ../, don't allow absolute paths.
        if os.path.isabs(path) or ".." in path.replace("\\", "/").split("/"):
            await ctx.send("``Refusing to read paths outside the bot's directory.``")
            return

        if not os.path.exists(path):
            cwd = os.getcwd()
            await ctx.send(f"``File not found:`` ``{path}``\n``Current working directory:`` ``{cwd}``")
            return

        if not os.path.isfile(path):
            await ctx.send(f"``That's a directory, not a file:`` ``{path}``")
            return

        size = os.path.getsize(path)

        with open(path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        # Small enough to inline in a code block
        if size < 1900:
            await ctx.send(f"```py\n{content}\n```")
            return

        # Otherwise send as a file attachment
        buffer = io.BytesIO(content.encode("utf-8"))
        filename = os.path.basename(path)
        await ctx.send(
            f"``File is {size} bytes, sending as an attachment instead of inline:``",
            file=discord.File(buffer, filename=filename)
        )

    @commands.command(name="dev-ls")
    async def dev_ls(self, ctx, path: str = "."):
        """Owner-only. Lists files in a directory on the bot's host."""
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

        lines = []
        for entry in entries:
            full = os.path.join(path, entry)
            marker = "/" if os.path.isdir(full) else ""
            lines.append(f"{entry}{marker}")

        listing = "\n".join(lines)
        await ctx.send(f"``Contents of`` ``{path}``:\n```\n{listing}\n```")

#commit
async def setup(bot):
    await bot.add_cog(Dev_Cat_File(bot))