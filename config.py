import discord
from enum import Enum

GUILD_ID = discord.Object(id=1324223207536070697)

ERROR = "<:Error:1511925664910147607>"
CHECK = "<:CheckMark:1512108503857238076>"
CHECKWHITE = "<:CheckMark2:1512309496947413012>"
X = "<:CrossMark:1511924485324804156>"
PERMISSON = "<:Permisson:1511924423819661442>"

class CommandType(Enum):
    USER = "User"
    MANAGER = "Manager"
    ADMIN = "Admin"

LOG_CHANNELS = {
    CommandType.USER: 0,
    CommandType.MANAGER: 0,
    CommandType.ADMIN: 0,
}

LOG_UNSUCCESSFUL = True
SERVER_ADMIN_ROLE_IDS = []
ADMIN_ROLE_IDS = []
MANAGER_ROLE_IDS = []
MEMBER_ROLE_IDS = []