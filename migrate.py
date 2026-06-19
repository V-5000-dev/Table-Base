import json

GUILD_ID = 1189678601205973002  # replace with your actual guild ID
SETTINGS_FILE = "settings.json"

with open(SETTINGS_FILE, "r") as f:
    old = json.load(f)

# If it's already migrated (top-level keys are guild IDs), stop
if all(k.isdigit() for k in old.keys()):
    print("Already in new format, nothing to do.")
else:
    new = {str(GUILD_ID): old}
    with open(SETTINGS_FILE, "w") as f:
        json.dump(new, f, indent=4)
    print(f"Migrated successfully under guild {GUILD_ID}.")