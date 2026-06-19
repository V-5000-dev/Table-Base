import discord
import json
import io
from discord.ext import commands
from config import CHECK, ERROR
import config

OWNER_ID = 1057431766568284360

SETTINGS_FILE = "settings.json"

# Keys present in the OLD, pre-multi-guild flat settings format.
# Used to detect that an uploaded file needs wrapping under a guild ID.
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
    """True if this looks like the OLD single-guild format (no guild ID wrapper)."""
    if not isinstance(data, dict):
        return False
    # If most of the expected flat keys are present at the top level, it's flat.
    return len(FLAT_FORMAT_KEYS & set(data.keys())) >= 5


def looks_like_wrapped_format(data: dict) -> bool:
    """True if every top-level key is already a numeric guild ID mapping to a dict."""
    if not isinstance(data, dict) or not data:
        return False
    return all(isinstance(k, str) and k.isdigit() and isinstance(v, dict) for k, v in data.items())


class Dev_Overwride_Json(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="dev-overwrite-json")
    async def dev_overwride_json(self, ctx, target_guild_id: int = None):
        """
        Owner-only. Attach a settings_export.json backup to this command
        to overwrite the live settings.json with it.

        - If the attached file is in the OLD flat format (no guild ID
          wrapper), it will be wrapped under target_guild_id (defaults to
          the guild this command is run in).
        - If the attached file is already in the NEW {guild_id: {...}}
          wrapped format, it's merged in as-is (other guilds' existing
          data on disk is preserved).
        """
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
            table_counts = {
                gid: len(g.get("ALL_TABLES", [])) for gid, g in new_entries.items()
            }
        elif looks_like_flat_format(uploaded_data):
            new_entries = {str(guild_id): uploaded_data}
            table_counts = {str(guild_id): len(uploaded_data.get("ALL_TABLES", []))}
        else:
            await ctx.send(
                f"{ERROR} ``Uploaded file doesn't look like a recognized settings format. "
                f"Nothing was changed.``"
            )
            return

        # Load whatever's currently on disk (if anything) so we only
        # overwrite the guild(s) present in the upload, not wipe everyone else.
        try:
            with open(SETTINGS_FILE, "r") as f:
                on_disk = json.load(f)
            if not isinstance(on_disk, dict):
                on_disk = {}
        except (FileNotFoundError, json.JSONDecodeError):
            on_disk = {}

        # If what's currently on disk is itself still in the old flat
        # format, don't merge garbage into the new structure — start clean.
        if looks_like_flat_format(on_disk) and not looks_like_wrapped_format(on_disk):
            on_disk = {}

        on_disk.update(new_entries)

        with open(SETTINGS_FILE, "w") as f:
            json.dump(on_disk, f, indent=4)

        # Reload into memory immediately so the running bot picks it up
        # without needing a restart.
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
            from config import CommandType
            settings["LOG_CHANNELS"][CommandType.USER]    = gdata.get("USER_LOG_CHANNEL", 0)
            settings["LOG_CHANNELS"][CommandType.MANAGER] = gdata.get("MANAGER_LOG_CHANNEL", 0)
            settings["LOG_CHANNELS"][CommandType.ADMIN]   = gdata.get("ADMIN_LOG_CHANNEL", 0)
            settings["ALL_TABLES"]               = gdata.get("ALL_TABLES", [])
            settings["COMMAND_PREFIX"]           = gdata.get("COMMAND_PREFIX", "t! ")

        summary = "\n".join(f"- Guild `{gid}`: {count} table(s)" for gid, count in table_counts.items())
        await ctx.send(
            f"{CHECK} ``Settings restored and reloaded into memory.``\n{summary}"
        )


async def setup(bot):
    await bot.add_cog(Dev_Overwride_Json(bot))