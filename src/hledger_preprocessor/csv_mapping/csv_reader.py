import csv
from dataclasses import dataclass
from typing import List

from typeguard import typechecked

from hledger_preprocessor.file_reading_and_writing import (
    assert_file_exists,
    detect_file_encoding,
)


@dataclass(frozen=True)
class CsvPreview:
    headers: List[str]
    sample_rows: List[List[str]]
    total_rows: int
    filepath: str


@typechecked
def read_csv_preview(
    *,
    csv_filepath: str,
    max_sample_rows: int = 10,
) -> CsvPreview:
    assert_file_exists(filepath=csv_filepath)
    encoding = detect_file_encoding(filepath=csv_filepath)

    with open(csv_filepath, encoding=encoding, errors="replace") as f:
        reader = csv.reader(f)
        all_rows = list(reader)

    if not all_rows:
        raise ValueError(f"CSV file is empty: {csv_filepath}")

    with open(csv_filepath, encoding=encoding, errors="replace") as f:
        sample = f.read(4096)
        try:
            has_header = csv.Sniffer().has_header(sample)
        except csv.Error:
            has_header = True  # assume header if sniffer fails

    if has_header:
        headers = all_rows[0]
        data_rows = all_rows[1:]
    else:
        headers = [f"Column_{i}" for i in range(len(all_rows[0]))]
        data_rows = all_rows

    return CsvPreview(
        headers=headers,
        sample_rows=data_rows[:max_sample_rows],
        total_rows=len(data_rows),
        filepath=csv_filepath,
    )
