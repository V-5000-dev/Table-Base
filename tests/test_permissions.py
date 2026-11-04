import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

import config
import utils
from config import CommandType
from conftest import make_member, make_table

MEMBER_A, MANAGER_A, ADMIN_A, SERVER_ADMIN = 10, 20, 30, 40


@pytest.fixture
def guild():
    settings = config.get_guild(1)
    settings["SERVER_ADMIN_ROLE_IDS"] = [SERVER_ADMIN]
    settings["ALL_TABLES"] = [
        make_table("A", member_role_ids=[MEMBER_A], manager_role_ids=[MANAGER_A], admin_role_ids=[ADMIN_A]),
        make_table("B"),
    ]
    return settings


@pytest.mark.parametrize("role,command_type,expected", [
    (MEMBER_A,  CommandType.USER,         True),
    (MEMBER_A,  CommandType.MANAGER,      False),
    (MANAGER_A, CommandType.USER,         True),
    (MANAGER_A, CommandType.MANAGER,      True),
    (MANAGER_A, CommandType.ADMIN,        False),
    (ADMIN_A,   CommandType.ADMIN,        True),
    (ADMIN_A,   CommandType.SERVER_ADMIN, False),
])
def test_roles_on_their_own_table(guild, role, command_type, expected):
    member = make_member(role_ids=[role])
    assert utils.has_table_access(member, guild, command_type, guild["ALL_TABLES"][0]) is expected


@pytest.mark.parametrize("role", [MEMBER_A, MANAGER_A, ADMIN_A])
def test_table_roles_do_not_reach_another_table(guild, role):
    member = make_member(role_ids=[role])
    assert utils.has_table_access(member, guild, CommandType.USER, guild["ALL_TABLES"][1]) is False


def test_server_admins_and_discord_admins_reach_every_table(guild):
    table_b = guild["ALL_TABLES"][1]
    assert utils.has_table_access(make_member(role_ids=[SERVER_ADMIN]), guild, CommandType.ADMIN, table_b)
    assert utils.has_table_access(make_member(administrator=True), guild, CommandType.SERVER_ADMIN, table_b)


def make_ctx(author, guild_id=1, client=None):
    return SimpleNamespace(
        author=author,
        bot=client or SimpleNamespace(get_channel=lambda channel_id: None),
        guild=SimpleNamespace(id=guild_id) if guild_id else None,
        command=SimpleNamespace(name="test"),
        send=AsyncMock(),
    )


def test_authorize_table_denies_a_manager_of_another_table(guild):
    ctx = make_ctx(make_member(role_ids=[MANAGER_A]))
    assert asyncio.run(utils.authorize_table(ctx, "B", CommandType.MANAGER)) is None
    assert "permission" in ctx.send.await_args.args[0]


def test_authorize_table_returns_the_table_to_its_manager(guild):
    ctx = make_ctx(make_member(role_ids=[MANAGER_A]))
    assert asyncio.run(utils.authorize_table(ctx, "A", CommandType.MANAGER))["name"] == "A"


def test_authorize_table_reports_an_unknown_table(guild):
    ctx = make_ctx(make_member(administrator=True))
    assert asyncio.run(utils.authorize_table(ctx, "Nope", CommandType.MANAGER)) is None
    assert "not found" in ctx.send.await_args.args[0]


def test_commands_in_dms_are_refused_without_crashing(guild):
    author = SimpleNamespace(id=1, mention="<@1>")  # A DM author has no guild_permissions.
    ctx = make_ctx(author, guild_id=None)
    assert asyncio.run(utils.authorize_table(ctx, "A", CommandType.USER)) is None
    assert "server" in ctx.send.await_args.args[0]


def test_autocomplete_in_dms_does_not_create_a_junk_guild():
    interaction = SimpleNamespace(guild_id=None)
    assert asyncio.run(utils.table_name_autocomplete(interaction, "")) == []
    assert None not in config.GUILD_SETTINGS


def test_server_admin_commands_log_to_the_admin_channel(guild):
    async def run():
        channel = SimpleNamespace(id=333, send=AsyncMock())
        guild["LOG_CHANNELS"][CommandType.ADMIN] = 333
        client = SimpleNamespace(get_channel=lambda channel_id: channel if channel_id == 333 else None)
        ctx = make_ctx(make_member(administrator=True), client=client)

        assert await utils.verifyCommandPermissions(ctx, CommandType.SERVER_ADMIN)
        await asyncio.gather(*utils._log_tasks)
        channel.send.assert_awaited_once()

    asyncio.run(run())


def test_a_broken_log_channel_does_not_break_the_command(guild):
    import discord

    async def run():
        response = SimpleNamespace(status=403, reason="Forbidden")
        channel = SimpleNamespace(id=333, send=AsyncMock(side_effect=discord.Forbidden(response, "no")))
        guild["LOG_CHANNELS"][CommandType.ADMIN] = 333
        client = SimpleNamespace(get_channel=lambda channel_id: channel)
        ctx = make_ctx(make_member(administrator=True), client=client)

        assert await utils.verifyCommandPermissions(ctx, CommandType.ADMIN)
        await asyncio.gather(*utils._log_tasks)

    asyncio.run(run())
