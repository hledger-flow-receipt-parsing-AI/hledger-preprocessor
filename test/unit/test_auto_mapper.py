from hledger_preprocessor.csv_mapping.auto_mapper import auto_map_columns
from hledger_preprocessor.csv_mapping.csv_reader import CsvPreview


def test_auto_map_triodos_columns():
    preview = CsvPreview(
        headers=[
            "Date",
            "Own Account",
            "Amount",
            "Debit/Credit",
            "Name",
            "Counter Account",
            "Code",
            "Description",
            "Balance",
        ],
        sample_rows=[
            [
                "01-01-2025",
                "NL12TRIO34",
                "100.00",
                "Debit",
                "Albert Heijn",
                "NL56INGB78",
                "BA",
                "Groceries",
                "1200.00",
            ],
        ],
        all_data_rows=[],
        total_rows=100,
        filepath="/tmp/triodos.csv",
    )
    mappings = auto_map_columns(csv_preview=preview)

    assert len(mappings) == 9

    fields_by_header = {m.csv_header: m.proposed_field for m in mappings}
    assert fields_by_header["Date"] == "the_date"
    assert fields_by_header["Amount"] == "tendered_amount_out"
    assert fields_by_header["Description"] == "description"
    assert fields_by_header["Name"] == "other_party_name"
    assert fields_by_header["Balance"] == "balance_after"


def test_auto_map_bitvavo_columns():
    preview = CsvPreview(
        headers=[
            "Timezone",
            "Date",
            "Time",
            "Type",
            "Currency",
            "Amount",
            "Quote Currency",
            "Quote Price",
            "Received / Paid Currency",
            "Received / Paid Amount",
            "Fee currency",
            "Fee amount",
            "Status",
            "Transaction ID",
            "Address",
        ],
        sample_rows=[
            [
                "Europe/Amsterdam",
                "2026-03-03",
                "21:53:03",
                "deposit",
                "EUR",
                "950",
                "",
                "",
                "",
                "",
                "EUR",
                "0",
                "Completed",
                "asdfasdf-w23r4-423423-92345-c0beac729b28",
                "NL73***68",
            ],
        ],
        all_data_rows=[],
        total_rows=50,
        filepath="/tmp/bitvavo.csv",
    )
    mappings = auto_map_columns(csv_preview=preview)

    assert len(mappings) == 15

    fields_by_header = {m.csv_header: m.proposed_field for m in mappings}
    assert fields_by_header["Date"] == "the_date"
    assert fields_by_header["Amount"] == "tendered_amount_out"
    assert fields_by_header["Currency"] == "payment_currency"
    # Type matches "transaction type" pattern
    assert fields_by_header["Type"] == "transaction_code"


def test_auto_map_unknown_headers_skip():
    preview = CsvPreview(
        headers=["Foo", "Bar", "Baz"],
        sample_rows=[["a", "b", "c"]],
        all_data_rows=[],
        total_rows=1,
        filepath="/tmp/unknown.csv",
    )
    mappings = auto_map_columns(csv_preview=preview)

    assert len(mappings) == 3
    # None of these should match known fields by header
    # but Bar/Baz might match substrings — check they are all None
    # since "foo", "bar", "baz" don't match any patterns
    for m in mappings:
        assert m.proposed_field is None


def test_auto_map_value_type_fallback():
    """When headers are unrecognisable, value-type detection kicks in."""
    preview = CsvPreview(
        headers=["Col_A", "Col_B", "Col_C"],
        sample_rows=[
            ["2025-01-01", "100.00", "hello"],
            ["2025-02-15", "200.50", "world"],
        ],
        all_data_rows=[],
        total_rows=2,
        filepath="/tmp/nolabels.csv",
    )
    mappings = auto_map_columns(csv_preview=preview)

    fields_by_header = {m.csv_header: m.proposed_field for m in mappings}
    assert fields_by_header["Col_A"] == "the_date"
    assert fields_by_header["Col_B"] == "tendered_amount_out"
    assert fields_by_header["Col_C"] is None


def test_no_duplicate_field_assignments():
    """Each field can only be assigned to one column."""
    preview = CsvPreview(
        headers=["Date", "Date2", "Amount", "Amount2"],
        sample_rows=[["2025-01-01", "2025-01-02", "100", "200"]],
        all_data_rows=[],
        total_rows=1,
        filepath="/tmp/dupes.csv",
    )
    mappings = auto_map_columns(csv_preview=preview)

    assigned = [m.proposed_field for m in mappings if m.proposed_field]
    assert len(assigned) == len(set(assigned)), "Duplicate field assignment"
