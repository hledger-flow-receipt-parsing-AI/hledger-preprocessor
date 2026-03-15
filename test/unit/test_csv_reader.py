import tempfile

from hledger_preprocessor.csv_mapping.csv_reader import read_csv_preview


def test_read_csv_preview_with_header():
    content = (
        "Date,Amount,Description\n"
        "2025-01-01,100.00,Groceries\n"
        "2025-01-02,50.00,Coffee\n"
    )
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".csv", delete=False
    ) as f:
        f.write(content)
        f.flush()
        preview = read_csv_preview(csv_filepath=f.name)

    assert preview.headers == ["Date", "Amount", "Description"]
    assert len(preview.sample_rows) == 2
    assert preview.total_rows == 2


def test_read_csv_preview_bitvavo():
    content = (
        "Timezone,Date,Time,Type,Currency,Amount,Quote Currency,Quote Price,"
        "Received / Paid Currency,Received / Paid Amount,Fee currency,"
        "Fee amount,Status,Transaction ID,Address\n"
        "Europe/Amsterdam,2026-03-03,21:53:03,deposit,EUR,950,,,,,EUR,0,"
        "Completed,asdfasdf-w23r4-423423-92345-c0beac729b28,NL73***68\n"
    )
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".csv", delete=False
    ) as f:
        f.write(content)
        f.flush()
        preview = read_csv_preview(csv_filepath=f.name)

    assert len(preview.headers) == 15
    assert preview.headers[0] == "Timezone"
    assert preview.headers[1] == "Date"
    assert preview.headers[5] == "Amount"
    assert preview.total_rows == 1
    assert len(preview.sample_rows) == 1


def test_read_csv_preview_max_sample_rows():
    # Use clearly-textual headers vs numeric data so Sniffer detects the header.
    lines = ["Name,Amount\n"] + [f"item{i},{i * 10}\n" for i in range(20)]
    content = "".join(lines)
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".csv", delete=False
    ) as f:
        f.write(content)
        f.flush()
        preview = read_csv_preview(csv_filepath=f.name, max_sample_rows=3)

    assert preview.headers == ["Name", "Amount"]
    assert preview.total_rows == 20
    assert len(preview.sample_rows) == 3
