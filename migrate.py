"""
One-time migration script.

Takes an OLD, flat-format settings.json (from before multi-guild support
was added) and wraps it under your server's guild ID, producing a NEW
settings.json that the current bot code can load correctly.

USAGE:
    1. Put your old/backup settings.json next to this script (or pass a path).
    2. Run:  python migrate_settings.py old_settings.json YOUR_GUILD_ID
    3. It writes settings_migrated.json next to it.
    4. Rename/replace your live settings.json on the bot's machine with that file.
    5. Restart the bot.

You can get your guild ID by enabling Developer Mode in Discord
(User Settings > Advanced > Developer Mode), then right-clicking your
server icon and choosing "Copy Server ID".
"""

import json
import sys
import os

EXPECTED_KEYS = {
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


def main():
    if len(sys.argv) != 3:
        print("Usage: python migrate_settings.py <old_settings.json> <guild_id>")
        sys.exit(1)

    old_path = sys.argv[1]
    guild_id_str = sys.argv[2]

    if not guild_id_str.isdigit():
        print(f"Error: guild_id must be a number, got: {guild_id_str!r}")
        sys.exit(1)

    if not os.path.exists(old_path):
        print(f"Error: file not found: {old_path}")
        sys.exit(1)

    with open(old_path, "r") as f:
        old_data = json.load(f)

    already_wrapped = all(
        isinstance(k, str) and k.isdigit() and isinstance(v, dict)
        for k, v in old_data.items()
    ) and len(old_data) > 0

    if already_wrapped:
        print("This file already looks like it's in the new {guild_id: {...}} format.")
        print("No migration needed — nothing was written.")
        sys.exit(0)

    unexpected = set(old_data.keys()) - EXPECTED_KEYS
    if unexpected:
        print(f"Note: found unexpected top-level keys, copying them as-is: {unexpected}")

    new_data = {guild_id_str: old_data}

    out_path = os.path.join(
        os.path.dirname(os.path.abspath(old_path)),
        "settings_migrated.json"
    )
    with open(out_path, "w") as f:
        json.dump(new_data, f, indent=4)

    table_count = len(old_data.get("ALL_TABLES", []))
    print(f"Done. Wrote: {out_path}")
    print(f"Wrapped under guild ID: {guild_id_str}")
    print(f"Tables carried over: {table_count}")
    print()
    print("Next step: replace your live settings.json on the bot's machine")
    print("with this file (rename it to settings.json), then restart the bot.")


if __name__ == "__main__":
    main()