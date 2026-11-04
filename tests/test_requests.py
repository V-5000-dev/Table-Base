import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import discord

import config
import utils
from cogs import add_row_by_request as request_cog
from cogs import table_settings
from conftest import make_member, make_table

MANAGER_ROLE = 20


def channel_client(channels):
    return SimpleNamespace(
        get_channel=channels.get,
        fetch_user=AsyncMock(return_value=SimpleNamespace(send=AsyncMock())),
    )


def fake_channel(message_id):
    return SimpleNamespace(send=AsyncMock(return_value=SimpleNamespace(id=message_id)))


def click(user, message_id, client=None):
    return SimpleNamespace(
        guild_id=1,
        user=user,
        client=client or channel_client({}),
        message=SimpleNamespace(id=message_id),
        response=SimpleNamespace(send_message=AsyncMock(), edit_message=AsyncMock()),
    )


def setup_guild():
    settings = config.get_guild(1)
    table_a = make_table("A", manager_role_ids=[MANAGER_ROLE])
    table_b = make_table("B")
    settings["ALL_TABLES"] = [table_a, table_b]
    return settings, table_a, table_b


def test_saving_a_request_channel_only_changes_that_table():
    async def run():
        settings, table_a, table_b = setup_guild()
        settings["TABLE_REQUEST_CHANNEL_ID"] = 500
        interaction = SimpleNamespace(response=SimpleNamespace(send_message=AsyncMock()))

        await table_settings.save_requestchannel_id(interaction, [SimpleNamespace(id=700, mention="#a")], table_a)

        assert settings["TABLE_REQUEST_CHANNEL_ID"] == 500
        assert utils.get_request_channel_id(table_a, settings) == 700
        assert utils.get_request_channel_id(table_b, settings) == 500

    asyncio.run(run())


def test_clearing_a_table_channel_falls_back_to_the_server_channel():
    async def run():
        settings, table_a, _ = setup_guild()
        settings["TABLE_REQUEST_CHANNEL_ID"] = 500
        table_a["request_channel_id"] = 700
        interaction = SimpleNamespace(response=SimpleNamespace(send_message=AsyncMock()))

        await table_settings.save_requestchannel_id(interaction, [], table_a)

        assert utils.get_request_channel_id(table_a, settings) == 500

    asyncio.run(run())


def test_requests_for_two_tables_go_to_their_own_channels():
    async def run():
        settings, table_a, table_b = setup_guild()
        table_a["request_channel_id"], table_b["request_channel_id"] = 701, 702
        channel_a, channel_b = fake_channel(1), fake_channel(2)
        client = channel_client({701: channel_a, 702: channel_b})
        requester = make_member(5)

        assert await request_cog.submit_request(client, settings, table_a, requester, {"Age": "1"}) is None
        assert await request_cog.submit_request(client, settings, table_b, requester, {"Age": "2"}) is None

        channel_a.send.assert_awaited_once()
        channel_b.send.assert_awaited_once()

    asyncio.run(run())


def submitted(values=None, existing=None):
    """Set up a table with one pending request, posted as message 900."""
    settings, table_a, _ = setup_guild()
    table_a["request_channel_id"] = 701
    if existing:
        utils.upsert_row(table_a, "<@5>", existing)
    client = channel_client({701: fake_channel(900)})
    return settings, table_a, client, values or {"Age": "21"}


def test_non_manager_cannot_review_and_nothing_changes():
    async def run():
        settings, table, client, values = submitted()
        await request_cog.submit_request(client, settings, table, make_member(5), values)

        interaction = click(make_member(5, role_ids=[1]), 900)
        assert await request_cog.AddRequest().interaction_check(interaction) is False
        assert table["data"] == []
        assert len(table["pending_requests"]) == 1

    asyncio.run(run())


def test_manager_of_another_table_cannot_review():
    async def run():
        settings, table, client, values = submitted()
        settings["ALL_TABLES"][1]["manager_role_ids"] = [77]
        await request_cog.submit_request(client, settings, table, make_member(5), values)

        assert await request_cog.AddRequest().interaction_check(click(make_member(6, role_ids=[77]), 900)) is False

    asyncio.run(run())


def test_table_manager_can_review():
    async def run():
        settings, table, client, values = submitted()
        await request_cog.submit_request(client, settings, table, make_member(5), values)

        assert await request_cog.AddRequest().interaction_check(click(make_member(6, role_ids=[MANAGER_ROLE]), 900))

    asyncio.run(run())


def test_accept_works_from_a_new_view_after_a_restart_and_shows_the_change():
    async def run():
        settings, table, client, _ = submitted(existing={"Age": "20", "City": "Oslo"})
        await request_cog.submit_request(client, settings, table, make_member(5), {"Age": "21", "City": "Oslo"})

        # A restart: everything is rebuilt from the file, and the view is a new object.
        utils.save_settings()
        config.GUILD_SETTINGS.clear()
        utils.load_settings()
        restarted_table = config.get_guild(1)["ALL_TABLES"][0]

        view = request_cog.AddRequest()
        interaction = click(make_member(6, role_ids=[MANAGER_ROLE]), 900, client)
        assert await view.interaction_check(interaction)
        await view.accept.callback(interaction)

        assert restarted_table["data"][0][2:] == ["21", "Oslo"]
        assert restarted_table["pending_requests"] == []

        kwargs = interaction.response.edit_message.await_args.kwargs
        fields = {f.name: f.value for f in kwargs["embed"].fields}
        assert fields["Age"] == "21"     # The Approved message keeps the change.
        assert "City" not in fields      # Unchanged columns stay hidden.
        assert all(child.disabled for child in kwargs["view"].children)

    asyncio.run(run())


def test_reject_does_not_touch_the_row():
    async def run():
        settings, table, client, values = submitted(existing={"Age": "20"})
        await request_cog.submit_request(client, settings, table, make_member(5), values)

        await request_cog.AddRequest().reject.callback(click(make_member(6, role_ids=[MANAGER_ROLE]), 900, client))

        assert table["data"][0][2] == "20"
        assert table["pending_requests"] == []

    asyncio.run(run())


def test_reject_survives_the_requesters_row_being_removed():
    async def run():
        settings, table, client, values = submitted(existing={"Age": "20"})
        await request_cog.submit_request(client, settings, table, make_member(5), values)
        table["data"].clear()

        interaction = click(make_member(6, role_ids=[MANAGER_ROLE]), 900, client)
        await request_cog.AddRequest().reject.callback(interaction)

        interaction.response.edit_message.assert_awaited_once()

    asyncio.run(run())


def test_request_for_a_deleted_table_does_not_report_approved():
    async def run():
        settings, table, client, values = submitted()
        await request_cog.submit_request(client, settings, table, make_member(5), values)
        settings["ALL_TABLES"].remove(table)

        interaction = click(make_member(6, administrator=True), 900)
        assert await request_cog.AddRequest().interaction_check(interaction) is False
        assert "no longer active" in interaction.response.send_message.await_args.args[0]

    asyncio.run(run())


def test_no_change_request_is_cancelled_and_not_posted():
    async def run():
        settings, table, client, _ = submitted(existing={"Age": "20", "City": "Oslo"})
        error = await request_cog.submit_request(client, settings, table, make_member(5), {"Age": "20"})

        assert "No changes" in error
        client.get_channel(701).send.assert_not_awaited()

    asyncio.run(run())


def test_failed_post_reports_an_error_and_leaves_nothing_pending():
    async def run():
        settings, table, client, values = submitted()
        response = SimpleNamespace(status=403, reason="Forbidden")
        client.get_channel(701).send = AsyncMock(side_effect=discord.Forbidden(response, "no"))

        error = await request_cog.submit_request(client, settings, table, make_member(5), values)

        assert "Could not post" in error
        assert not table.get("pending_requests")

    asyncio.run(run())


def test_every_request_button_is_persistent():
    async def run():
        view = request_cog.AddRequest()
        assert view.is_persistent()
        assert {c.custom_id for c in view.children} == {"table_request:accept", "table_request:reject"}

    asyncio.run(run())


def test_modal_prefills_from_the_current_row_and_blank_keeps_it():
    async def run():
        settings, table, client, _ = submitted(existing={"Age": "20"})
        modal = request_cog.AddRow_Input(table, "<@5>")
        assert [i.default for i in modal.inputs] == ["20", None]

        for text_input, value in zip(modal.inputs, ["", "Rome"]):
            text_input._value = value
        interaction = SimpleNamespace(
            guild_id=1, user=make_member(5), client=client,
            response=SimpleNamespace(send_message=AsyncMock()),
        )
        await modal.on_submit(interaction)

        assert table["pending_requests"][0]["values"] == {"City": "Rome"}

    asyncio.run(run())


def test_long_column_names_fit_the_modal_label_limit():
    async def run():
        table = make_table(columns=("x" * 50,))
        modal = request_cog.AddRow_Input(table, "<@5>")
        assert len(modal.inputs[0].label) <= 45

    asyncio.run(run())


def test_selects_show_current_values_and_can_be_emptied():
    async def run():
        channel = MagicMock(spec=discord.TextChannel)
        channel.id = 700
        role = MagicMock(spec=discord.Role)
        role.id = 20
        guild = SimpleNamespace(get_channel=lambda i: channel, get_role=lambda i: role)
        ctx = SimpleNamespace(guild=guild, author=make_member())

        channel_select = utils.SelectChannels_Menu(None, ctx, 700)
        role_select = utils.SelectRoles_Menu(None, ctx, [20])

        assert channel_select.min_values == 0 and role_select.min_values == 0
        assert [d["id"] for d in channel_select.to_component_dict()["default_values"]] == [700]
        assert [d["id"] for d in role_select.to_component_dict()["default_values"]] == [20]

        empty = utils.SelectChannels_Menu(None, ctx)
        assert not empty.to_component_dict().get("default_values")

    asyncio.run(run())
