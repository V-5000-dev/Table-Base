import os
import sys
from types import SimpleNamespace

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import config
import utils


@pytest.fixture(autouse=True)
def isolated_settings(tmp_path, monkeypatch):
    """Keep every test away from the real settings.json."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(utils, "SETTINGS_FILE", str(tmp_path / "settings.json"))
    config.GUILD_SETTINGS.clear()
    yield
    config.GUILD_SETTINGS.clear()


def make_member(user_id=1, role_ids=(), administrator=False):
    return SimpleNamespace(
        id=user_id,
        mention=f"<@{user_id}>",
        guild_permissions=SimpleNamespace(administrator=administrator),
        roles=[SimpleNamespace(id=r) for r in role_ids],
    )


def make_table(name="A", columns=("Age", "City"), **extra):
    table = {
        "name": name,
        "rows": 0,
        "columns": 2 + len(columns),
        "column_names": ["User", "Timestamp", *columns],
        "member_role_ids": [],
        "ping_managers": True,
        "data": [],
    }
    table.update(extra)
    return table
