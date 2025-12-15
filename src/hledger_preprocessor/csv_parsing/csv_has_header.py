import csv

from typeguard import typechecked


@typechecked
def has_header0(*, csv_file_path: str, sample_size=4096):
    with open(csv_file_path, newline="", encoding="utf-8") as f:
        try:
            csv.Sniffer().sniff(f.read(sample_size))
            f.seek(0)
            has_header = csv.Sniffer().has_header(f.read(sample_size))
            return has_header
        except csv.Error:
            # Sniffer can fail on some edge cases (e.g., inconsistent quoting)
            return None  # or fall back to other methods
