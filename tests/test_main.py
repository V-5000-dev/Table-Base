"""Starts the real main.py without connecting to Discord."""
import asyncio
import json
import os
import runpy
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import discord
import pytest
from discord.ext import commands

import config
from conftest import ROOT, make_table

EXPECTED_SLASH = {
    "ping", "prefix", "set-prefix", "create-table", "delete-table", "table-settings", "server-settings",
    "view-table", "view-row", "view-row-by-user", "view-row-by-value", "view-row-by-id",
    "add-row-by-user", "add-row-by-request", "remove-row-by-id", "remove-row-by-user",
}


@pytest.fixture
def main_module(monkeypatch):
    monkeypatch.setattr(discord.Client, "run", lambda self, *a, **k: None)
    return runpy.run_path(os.path.join(ROOT, "main.py"))


def boot(client):
    async def start():
        client.tree.sync = AsyncMock(return_value=[])
        await client._async_setup_hook()
        await client.setup_hook()
    return start()


def test_all_cogs_load_and_register_their_commands(main_module):
    client = main_module["client"]

    async def run():
        await boot(client)
        assert {c.name for c in client.tree.get_commands()} == EXPECTED_SLASH
        assert "remove-row-by-user" in {c.name for c in client.commands}
        assert "restore-settings" in {c.name for c in client.commands}
        assert client.persistent_views, "the request buttons were not registered"
        client.get_cog("Dev_Control").expire_keys.cancel()
        await client.close()

    asyncio.run(run())


def test_a_failing_backup_does_not_stop_the_others(main_module):
    client = main_module["client"]

    async def run():
        response = SimpleNamespace(status=403, reason="Forbidden")
        broken = SimpleNamespace(send=AsyncMock(side_effect=discord.Forbidden(response, "no")))
        working = SimpleNamespace(send=AsyncMock())
        config.get_guild(1)["TABLE_BACKUP_CHANNEL_ID"] = 11
        config.get_guild(2)["TABLE_BACKUP_CHANNEL_ID"] = 22
        config.get_guild(2)["ALL_TABLES"].append(make_table(request_channel_id=5))
        client.get_channel = {11: broken, 22: working}.get

        await client.backup_tables.coro(client)

        working.send.assert_awaited_once()
        backup = json.loads(working.send.await_args.kwargs["file"].fp.read())
        assert backup["2"]["ALL_TABLES"][0]["request_channel_id"] == 5
        assert "USER_LOG_CHANNEL" in backup["2"]

    asyncio.run(run())


def test_wrong_arguments_get_a_reply(main_module):
    client = main_module["client"]

    async def run():
        ctx = SimpleNamespace(
            send=AsyncMock(), clean_prefix="t!",
            command=SimpleNamespace(qualified_name="view-row", signature="<name>"),
        )
        param = MagicMock()
        param.displayed_name = "name"
        param.name = "name"
        await client.on_command_error(ctx, commands.MissingRequiredArgument(param))
        assert "Usage" in ctx.send.await_args.args[0]

    asyncio.run(run())


def test_non_owners_get_silence_from_owner_commands(main_module):
    client = main_module["client"]

    async def run():
        ctx = SimpleNamespace(send=AsyncMock())
        await client.on_command_error(ctx, commands.CheckFailure())
        ctx.send.assert_not_awaited()

    asyncio.run(run())
