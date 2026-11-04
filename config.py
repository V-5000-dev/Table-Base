# config.py
from enum import Enum

ERROR = "<:Error:1511923491107246141>"
CHECK = "<:CheckMark:1512108503857238076>"
X = "<:CrossMark:1511924485324804156>"
PERMISSON = "<:Permisson:1511924423819661442>"
DANDER = "<:DangerCommand:1511923466016657438>"
ADMIN = "<:AdminCommand:1511923466016657438>"  
USER = "<:UserCommand:1512608514919632896>"
MANAGER = "<:ManagerCommand:1512608289819463762>"


DEFAULT_PREFIX = "t!"

# The one value stored in a table cell that has no content.
EMPTY_CELL = "None"

MAX_COLUMNS_NOTE = "This table has too many columns to add a row via this command (max 20 supported)."


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
        "LOG_UNSUCCESSFUL": True,
        "LOG_CHANNELS": {
            CommandType.USER: 0,
            CommandType.MANAGER: 0,
            CommandType.ADMIN: 0,
        },
        "ALL_TABLES": [],
        "COMMAND_PREFIX": DEFAULT_PREFIX,
        "KEY_EXPIRIES": {},
    }


GUILD_SETTINGS: dict[int, dict] = {}


def get_guild(guild_id: int) -> dict:
    """Get settings for a guild, creating defaults if not present."""
    if guild_id not in GUILD_SETTINGS:
        GUILD_SETTINGS[guild_id] = default_guild_settings()
    return GUILD_SETTINGS[guild_id]