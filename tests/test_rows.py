import utils
from config import EMPTY_CELL
from conftest import make_table


def test_add_then_update_keeps_untouched_columns():
    table = make_table()
    assert utils.upsert_row(table, "<@1>", {"Age": "20", "City": "Oslo"}) is False
    assert utils.upsert_row(table, "<@1>", {"Age": "21"}) is True

    assert table["rows"] == 1
    assert table["data"][0][2:] == ["21", "Oslo"]


def test_update_goes_to_the_right_user_after_rows_shift():
    table = make_table()
    utils.upsert_row(table, "<@1>", {"Age": "1"})
    utils.upsert_row(table, "<@2>", {"Age": "2"})
    utils.upsert_row(table, "<@3>", {"Age": "3"})

    del table["data"][0]  # A row is removed while a modal is open.
    utils.upsert_row(table, "<@3>", {"Age": "33"})

    assert [(r[0], r[2]) for r in table["data"]] == [("<@2>", "2"), ("<@3>", "33")]


def test_row_stays_aligned_when_columns_changed_after_values_were_collected():
    table = make_table(columns=("Age", "City", "Pet"))
    utils.upsert_row(table, "<@1>", {"Age": "20", "City": "Oslo", "Pet": "Cat"})
    stale_values = {"City": "Rome", "Pet": "Dog"}

    index = table["column_names"].index("Age")
    table["column_names"].pop(index)
    table["data"][0].pop(index)
    table["column_names"].append("Food")
    table["data"][0].append(EMPTY_CELL)

    utils.upsert_row(table, "<@1>", stale_values)

    row = dict(zip(table["column_names"], table["data"][0]))
    assert (row["City"], row["Pet"], row["Food"]) == ("Rome", "Dog", EMPTY_CELL)
    assert len(table["data"][0]) == len(table["column_names"])


def test_blank_input_means_keep():
    for value in ("", "None", "none", "null", "NULL"):
        assert utils.is_blank_input(value)
    assert not utils.is_blank_input("Nonesuch")


def test_widest_possible_row_fits_embed_limits():
    columns = ["User", "Timestamp"] + [f"C{'x' * 43}{i:02}"[:45] for i in range(20)]
    row = ["<@1>", "<t:1:f>"] + ["y" * 200] * 20

    pages = utils.paginate_blocks([utils.format_row(columns, row)])

    assert len(pages) >= 2
    assert all(len(page) <= 4096 for page in pages)
    assert "\n".join(pages).count("y" * 200) == 20


def test_a_large_table_pages_within_limits():
    columns = ["User", "Timestamp", "Notes"]
    blocks = [f"**Row {i}**\n" + utils.format_row(columns, ["<@1>", "t", "z" * 200]) for i in range(300)]

    pages = utils.paginate_blocks(blocks)

    assert all(len(page) <= 4096 for page in pages)
    assert sum(page.count("**Row ") for page in pages) == 300


def test_table_name_rules():
    assert utils.table_name_error("Valid name") is None
    assert utils.table_name_error("")
    assert utils.table_name_error("x" * 51)
