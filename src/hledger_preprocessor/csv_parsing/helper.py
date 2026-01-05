from datetime import datetime

import iso8601
from typeguard import typechecked


@typechecked
def read_date(*, the_date_str: str) -> datetime:
    if not the_date_str or the_date_str == "None":
        raise ValueError(f"Invalid or missing the_date str")
    try:
        # Try new format: YYYY-MM-DD-HH-MM-SS
        the_date = datetime.strptime(the_date_str, "%Y-%m-%d-%H-%M-%S").replace(
            tzinfo=None
        )
    except ValueError:
        try:
            # Fallback for legacy ISO 8601 or YYYY-MM-DD
            the_date = iso8601.parse_date(the_date_str).replace(tzinfo=None)
        except iso8601.ParseError:
            raise ValueError(f"Failed to parse the_date {the_date_str}")
    return the_date
