import asyncio
import io
import json
import subprocess
import time
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import discord
import pytest

import config
import utils
from cogs import dev_control
from config import CommandType
from conftest import make_table


def git_result(code=0, out="", err=""):
    return subprocess.CompletedProcess(["git"], code, out, err)


def test_reset_is_skipped_when_fetch_fails(monkeypatch):
    calls = []

    async def fake_git(*args):
        calls.append(args[0])
        return git_result(1, err="network down")

    monkeypatch.setattr(dev_control, "run_git", fake_git)
    updated, output = asyncio.run(dev_control.update_to("main"))

    assert updated is False
    assert calls == ["fetch"]
    assert "network down" in output


def test_git_timeout_is_reported_not_raised(monkeypatch):
    def slow(*args, **kwargs):
        raise subprocess.TimeoutExpired("git", 60)

    monkeypatch.setattr(dev_control.subprocess, "run", slow)
    result = asyncio.run(dev_control.run_git("push", "origin", "main"))

    assert result.returncode == 1
    assert "timed out" in result.stderr


def make_cog():
    bot = MagicMock()
    return dev_control.Dev_Control(bot), bot


def owner_ctx(**extra):
    message = SimpleNamespace(delete=AsyncMock(), attachments=extra.pop("attachments", []))
    return SimpleNamespace(
        author=SimpleNamespace(id=dev_control.OWNER_ID),
        message=message,
        send=AsyncMock(),
        guild=extra.pop("guild", SimpleNamespace(id=1)),
        **extra,
    )


def test_update_with_long_output_still_restarts(monkeypatch):
    async def run():
        monkeypatch.setattr(dev_control, "update_to", AsyncMock(return_value=(True, "x" * 5000)))
        execv = MagicMock()
        monkeypatch.setattr(dev_control.os, "execv", execv)
        cog, _ = make_cog()
        ctx = owner_ctx()

        await cog.dev_update.callback(cog, ctx)

        embed = ctx.send.await_args_list[0].kwargs["embed"]
        assert len(embed.fields[0].value) <= 1024
        execv.assert_called_once()

    asyncio.run(run())


def test_only_the_owner_passes_the_cog_check():
    async def run():
        cog, _ = make_cog()
        assert await cog.cog_check(SimpleNamespace(author=SimpleNamespace(id=dev_control.OWNER_ID)))
        assert not await cog.cog_check(SimpleNamespace(author=SimpleNamespace(id=1)))

    asyncio.run(run())


def test_commands_survive_being_unable_to_delete_the_message(monkeypatch):
    async def run():
        execv = MagicMock()
        monkeypatch.setattr(dev_control.os, "execv", execv)
        cog, _ = make_cog()
        ctx = owner_ctx()
        response = SimpleNamespace(status=403, reason="Forbidden")
        ctx.message.delete = AsyncMock(side_effect=discord.Forbidden(response, "no"))

        await cog.dev_restart.callback(cog, ctx)

        execv.assert_called_once()

    asyncio.run(run())


@pytest.mark.parametrize("path", [".env", "file.env", "cogs/.env", ".env.local"])
def test_cat_refuses_secret_files(path):
    async def run():
        cog, _ = make_cog()
        ctx = owner_ctx()
        await cog.dev_cat.callback(cog, ctx, path)
        assert "Refusing" in ctx.send.await_args.args[0]

    asyncio.run(run())


def test_ls_on_a_file_replies_instead_of_crashing(tmp_path):
    async def run():
        (tmp_path / "a.txt").write_text("x")
        cog, _ = make_cog()
        ctx = owner_ctx()
        await cog.dev_ls.callback(cog, ctx, "a.txt")
        assert "a file" in ctx.send.await_args.args[0]

    asyncio.run(run())


def test_long_ls_is_sent_as_a_file(tmp_path):
    async def run():
        for i in range(200):
            (tmp_path / f"long_file_name_number_{i}.txt").write_text("x")
        cog, _ = make_cog()
        ctx = owner_ctx()
        await cog.dev_ls.callback(cog, ctx)
        assert "file" in ctx.send.await_args.kwargs

    asyncio.run(run())


def test_servers_handles_unknown_member_count():
    async def run():
        cog, bot = make_cog()
        bot.guilds = [
            SimpleNamespace(name="a", member_count=None, owner_id=1),
            SimpleNamespace(name="b", member_count=3, owner_id=2),
        ]
        ctx = owner_ctx()
        await cog.dev_servers.callback(cog, ctx)
        assert ctx.send.await_args.kwargs["embed"].description.startswith("`b`")

    asyncio.run(run())


def key_setup(has_role_after_fetch=False):
    role = SimpleNamespace(id=dev_control.ROLE_ID_TO_ADD)
    member = SimpleNamespace(
        id=5, mention="<@5>", roles=[role] if has_role_after_fetch else [],
        add_roles=AsyncMock(), remove_roles=AsyncMock(),
    )
    guild = SimpleNamespace(id=1, get_role=lambda i: role, fetch_member=AsyncMock(return_value=member))
    return role, member, guild


def test_timed_key_is_saved_and_survives_a_restart():
    async def run():
        _, member, guild = key_setup()
        cog, _ = make_cog()
        ctx = owner_ctx(guild=guild, channel=SimpleNamespace(id=70))

        await cog.dev_key.callback(cog, ctx, member, 2)

        member.add_roles.assert_awaited_once()
        config.GUILD_SETTINGS.clear()
        utils.load_settings()
        assert config.get_guild(1)["KEY_EXPIRIES"]["5"]["channel_id"] == 70

    asyncio.run(run())


def test_expired_key_is_removed_even_when_the_cached_member_looks_roleless():
    async def run():
        role, member, guild = key_setup()  # Fresh or stale, removal does not depend on .roles.
        cog, bot = make_cog()
        bot.get_guild = lambda i: guild
        channel = SimpleNamespace(send=AsyncMock())
        bot.get_channel = lambda i: channel
        settings = config.get_guild(1)
        settings["KEY_EXPIRIES"]["5"] = {"expires_at": time.time() - 1, "channel_id": 70}

        await cog.expire_keys.coro(cog)

        member.remove_roles.assert_awaited_once_with(role)
        assert settings["KEY_EXPIRIES"] == {}
        channel.send.assert_awaited_once()

    asyncio.run(run())


def test_unexpired_key_is_left_alone():
    async def run():
        _, member, guild = key_setup()
        cog, bot = make_cog()
        bot.get_guild = lambda i: guild
        settings = config.get_guild(1)
        settings["KEY_EXPIRIES"]["5"] = {"expires_at": time.time() + 999, "channel_id": 70}

        await cog.expire_keys.coro(cog)

        member.remove_roles.assert_not_awaited()
        assert "5" in settings["KEY_EXPIRIES"]

    asyncio.run(run())


def test_failed_key_removal_is_retried():
    async def run():
        _, member, guild = key_setup()
        response = SimpleNamespace(status=403, reason="Forbidden")
        member.remove_roles = AsyncMock(side_effect=discord.Forbidden(response, "no"))
        cog, bot = make_cog()
        bot.get_guild = lambda i: guild
        settings = config.get_guild(1)
        settings["KEY_EXPIRIES"]["5"] = {"expires_at": 0, "channel_id": 70}

        await cog.expire_keys.coro(cog)

        assert "5" in settings["KEY_EXPIRIES"]

    asyncio.run(run())


def test_key_rejects_invalid_hours():
    async def run():
        _, member, guild = key_setup()
        cog, _ = make_cog()
        ctx = owner_ctx(guild=guild)
        await cog.dev_key.callback(cog, ctx, member, float("inf"))
        member.add_roles.assert_not_awaited()

    asyncio.run(run())


def attachment(data):
    return SimpleNamespace(filename="settings.json", read=AsyncMock(return_value=json.dumps(data).encode()))


def test_restore_of_an_old_format_backup_keeps_log_channels():
    async def run():
        backup = {"7": {
            "ALL_TABLES": [make_table()],
            "LOG_CHANNELS": {"USER": 111, "MANAGER": 222, "ADMIN": 333, "SERVER_ADMIN": 0},
        }}
        cog, _ = make_cog()
        ctx = owner_ctx(attachments=[attachment(backup)])

        await cog.dev_restore_settings.callback(cog, ctx)

        assert config.get_guild(7)["LOG_CHANNELS"][CommandType.ADMIN] == 333
        with open(utils.SETTINGS_FILE) as f:
            assert json.load(f)["7"]["ADMIN_LOG_CHANNEL"] == 333

    asyncio.run(run())


def test_restore_applies_the_target_guild_to_a_single_guild_file():
    async def run():
        cog, _ = make_cog()
        ctx = owner_ctx(attachments=[attachment({"7": {"ALL_TABLES": [make_table()]}})])

        await cog.dev_restore_settings.callback(cog, ctx, 8)

        assert len(config.get_guild(8)["ALL_TABLES"]) == 1
        assert 7 not in config.GUILD_SETTINGS

    asyncio.run(run())


def test_restore_refuses_a_target_guild_for_a_multi_guild_file():
    async def run():
        cog, _ = make_cog()
        ctx = owner_ctx(attachments=[attachment({"7": {}, "9": {}})])

        await cog.dev_restore_settings.callback(cog, ctx, 8)

        assert "Nothing was changed" in ctx.send.await_args.args[0]
        assert 8 not in config.GUILD_SETTINGS

    asyncio.run(run())
