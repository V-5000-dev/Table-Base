import json

import pytest

import config
import utils
from config import CommandType, EMPTY_CELL
from conftest import make_table


def test_backup_then_restore_keeps_log_channels_and_table_channel():
    settings = config.get_guild(1)
    settings["LOG_CHANNELS"][CommandType.USER] = 111
    settings["LOG_CHANNELS"][CommandType.MANAGER] = 222
    settings["LOG_CHANNELS"][CommandType.ADMIN] = 333
    settings["ALL_TABLES"].append(make_table(request_channel_id=999))

    backup = json.loads(json.dumps(utils.serialize_guild(settings)))

    restored = config.default_guild_settings()
    utils.apply_guild_data(restored, backup)

    assert restored["LOG_CHANNELS"][CommandType.USER] == 111
    assert restored["LOG_CHANNELS"][CommandType.MANAGER] == 222
    assert restored["LOG_CHANNELS"][CommandType.ADMIN] == 333
    assert restored["ALL_TABLES"][0]["request_channel_id"] == 999


def test_backups_already_posted_in_the_old_format_still_restore():
    old_backup = {"LOG_CHANNELS": {"USER": 111, "MANAGER": 222, "ADMIN": 333, "SERVER_ADMIN": 0}}
    restored = config.default_guild_settings()
    utils.apply_guild_data(restored, old_backup)

    assert restored["LOG_CHANNELS"][CommandType.USER] == 111
    assert restored["LOG_CHANNELS"][CommandType.ADMIN] == 333


def test_old_empty_values_are_normalised_and_short_rows_padded():
    table = make_table(data=[["<@1>", "t", "null", ""], ["<@2>", "t", "x"]])
    utils.normalize_table(table)

    assert table["data"][0] == ["<@1>", "t", EMPTY_CELL, EMPTY_CELL]
    assert table["data"][1] == ["<@2>", "t", "x", EMPTY_CELL]


def test_save_then_load_round_trip():
    config.get_guild(1)["ALL_TABLES"].append(make_table(request_channel_id=5))
    utils.save_settings()

    config.GUILD_SETTINGS.clear()
    utils.load_settings()

    assert config.get_guild(1)["ALL_TABLES"][0]["request_channel_id"] == 5


def test_failed_write_leaves_the_existing_file_intact(monkeypatch):
    config.get_guild(1)["COMMAND_PREFIX"] = "!"
    utils.save_settings()

    def broken_dump(*args, **kwargs):
        raise OSError("disk full")

    with monkeypatch.context() as patch:
        patch.setattr(utils.json, "dump", broken_dump)
        with pytest.raises(OSError):
            utils.save_settings()

    with open(utils.SETTINGS_FILE) as f:
        assert json.load(f)["1"]["COMMAND_PREFIX"] == "!"


def test_corrupt_file_does_not_stop_startup_and_is_kept(tmp_path, monkeypatch):
    monkeypatch.setattr(utils, "SETTINGS_FILE", str(tmp_path / "settings.json"))
    (tmp_path / "settings.json").write_text('{"1": {"ALL_TAB')

    utils.load_settings()
    utils.save_settings()

    kept = list(tmp_path.glob("settings.json.corrupt-*"))
    assert len(kept) == 1
    assert kept[0].read_text() == '{"1": {"ALL_TAB'
