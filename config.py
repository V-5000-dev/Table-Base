# config.py
from enum import Enum
import discord

GUILD_ID = discord.Object(id=1324223207536070697)

ERROR = "<:Error:1511923491107246141>"
CHECK = "<:CheckMark:1512108503857238076>"
X = "<:CrossMark:1511924485324804156>"
PERMISSON = "<:Permisson:1511924423819661442>"
DANDER = "<:DangerCommand:1511923466016657438>"
ADMIN = "<:AdminCommand:1511923466016657438>"  
USER = "<:UserCommand:1512608514919632896>"
MANAGER = "<:ManagerCommand:1512608289819463762>"


class CommandType(Enum):
    USER = "User"
    MANAGER = "Manager"
    ADMIN = "Admin"
    SERVER_ADMIN = "ServerAdmin"  # was missing


# config.py

def default_guild_settings():
    return {
        "TABLE_REQUEST_CHANNEL_ID": 0,
        "TABLE_BACKUP_CHANNEL_ID": 0,
        "SERVER_ADMIN_ROLE_IDS": [],
        "ADMIN_ROLE_IDS": [],
        "MANAGER_ROLE_IDS": [],
        "MEMBER_ROLE_IDS": [],
        "LOG_UNSUCCESSFUL": True,
        "LOG_CHANNELS": {         
            CommandType.USER: 0,
            CommandType.MANAGER: 0,
            CommandType.ADMIN: 0,
            CommandType.SERVER_ADMIN: 0,
        },
        "ALL_TABLES": [],
        "COMMAND_PREFIX": "t!",
    }


GUILD_SETTINGS: dict[int, dict] = {}


def get_guild(guild_id: int) -> dict:
    """Get settings for a guild, creating defaults if not present."""
    if guild_id not in GUILD_SETTINGS:
        GUILD_SETTINGS[guild_id] = default_guild_settings()
    return GUILD_SETTINGS[guild_id]