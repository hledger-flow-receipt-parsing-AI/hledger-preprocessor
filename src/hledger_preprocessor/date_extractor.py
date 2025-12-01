import re
from datetime import datetime
from typing import Dict, List, Optional

import dateutil.parser as date_parser
from typeguard import typechecked


@typechecked
def get_date_from_bank_date_or_shop_date_description(
    *, bank_date_str: str, description: str
) -> datetime:
    bank_date: datetime = parse_date(bank_date_str)

    description_dates: List[Dict[str, str | datetime]] = extract_dates_times(
        description=description
    )
    if len(description_dates) == 1:  # If only 1 date is found in description.

        # Get the date time from the description.
        parsed_shop_date: datetime = description_dates[0]["datetime"].replace(
            tzinfo=None
        )

        # Banks process transactions up to 10 days after a shop sends it. Yet, in parsing the description, the month and day may be swapped, the minimum error this yields (e.g. march 4 vs april 3rd is 27 days, if that is the case, just use the bank statement date.)
        # TODO: move margin=10 to config.
        margin: int = 10

        # TODO: use this check to train an AI (instead of using extract_dates_times().
        # TODO: double check the logic in this bit.
        if is_within_date_range(a=bank_date, b=parsed_shop_date, margin=margin):
            return parsed_shop_date  # Return the original string if likely day/month swapped
        else:
            if can_swap_day_and_month(some_date=parsed_shop_date):
                swapped_description_date: datetime = swap_month_day(
                    some_date=parsed_shop_date
                ).replace(tzinfo=None)
                if is_within_date_range(
                    a=bank_date, b=swapped_description_date, margin=margin
                ):
                    return swapped_description_date
                else:
                    # Swap did not yield a solution.
                    return parsed_shop_date
            else:
                return parsed_shop_date
    return bank_date


@typechecked
def is_within_date_range(*, a: datetime, b: datetime, margin: int) -> bool:
    delta = abs(a - b).days
    return delta <= margin


@typechecked
def parse_date(date_string: str, date_format: str = "%d-%m-%Y") -> datetime:
    return datetime.strptime(date_string, date_format)


@typechecked
def get_month_from_date(*, date_str: str) -> Optional[int]:
    """
    Extracts the month from a suspected date string.
    Returns the month (1-12) or None if not found.
    """
    try:
        parsed_dt = date_parser.parse(date_str, fuzzy=False)
        return parsed_dt.month
    except (ValueError, TypeError):
        return None


@typechecked
def get_year_from_date(*, date_str: str) -> Optional[int]:
    """
    Extracts the year from a suspected date string.
    Returns the year (e.g., 2025) or None if not found.
    """
    try:
        parsed_dt = date_parser.parse(date_str, fuzzy=False)
        return parsed_dt.year
    except (ValueError, TypeError):
        return None


@typechecked
def get_day_from_date(*, date_str: str) -> Optional[int]:
    """
    Extracts the day from a suspected date string.
    Returns the day (1-31) or None if not found.
    """
    try:
        parsed_dt = date_parser.parse(date_str, fuzzy=False)
        return parsed_dt.day
    except (ValueError, TypeError):
        return None


@typechecked
def get_hour_from_date(*, date_str: str) -> Optional[int]:
    """
    Extracts the hour from a suspected date string.
    Returns the hour (0-23) or None if not found.
    """
    try:
        parsed_dt = date_parser.parse(date_str, fuzzy=False)
        return parsed_dt.hour
    except (ValueError, TypeError):
        return None


@typechecked
def get_minute_from_date(*, date_str: str) -> Optional[int]:
    """
    Extracts the minute from a suspected date string.
    Returns the minute (0-59) or None if not found.
    """
    try:
        parsed_dt = date_parser.parse(date_str, fuzzy=False)
        return parsed_dt.minute
    except (ValueError, TypeError):
        return None


@typechecked
def extract_dates_times(*, description: str) -> List[Dict[str, str | datetime]]:
    """
    Extracts all dates and times from a description, supporting multiple formats.
    Returns a list of dictionaries containing parsed datetime objects and their original strings.
    """
    if not description or not isinstance(description, str):
        return []

    # Comprehensive regex patterns for various date and time formats
    date_patterns = [
        # Date with time (e.g., "2025-01-12 14:30", "03-04-2025 17:54")
        r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4}\s+\d{1,2}:\d{2}(?::\d{2})?\s*(?:AM|PM|am|pm)?\b",
        r"\b\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}\s+\d{1,2}:\d{2}(?::\d{2})?\s*(?:AM|PM|am|pm)?\b",
        r"\b\d{4}[-/]\d{1,2}[-/]\d{1,2}\s+\d{1,2}:\d{2}(?::\d{2})?\s*(?:AM|PM|am|pm)?\b",
        r"\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\s+\d{1,2}:\d{2}(?::\d{2})?\s*(?:AM|PM|am|pm)?\b",
        # Full date formats (e.g., "January 12, 2025", "12 Jan 2025", "2025-01-12")
        r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4}\b",
        r"\b\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}\b",
        r"\b\d{4}[-/]\d{1,2}[-/]\d{1,2}\b",
        r"\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b",
        # Standalone time (e.g., "14:30", "2:30 PM")
        r"\b\d{1,2}:\d{2}(?::\d{2})?\s*(?:AM|PM|am|pm)?\b",
    ]

    results: List[Dict[str, datetime]] = []
    seen_dates = set()  # Track unique dates to avoid duplicates

    # Combine all patterns and find matches
    combined_pattern = "|".join(f"({pattern})" for pattern in date_patterns)
    matches = re.finditer(combined_pattern, description, re.IGNORECASE)

    for match in matches:
        date_str = match.group(0)
        try:
            # Skip standalone times to avoid incorrect default dates
            if re.match(
                r"\b\d{1,2}:\d{2}(?::\d{2})?\s*(?:AM|PM|am|pm)?\b",
                date_str,
                re.IGNORECASE,
            ):
                continue

            # Use component functions to validate date/time
            month = get_month_from_date(date_str=date_str)
            year = get_year_from_date(date_str=date_str)
            day = get_day_from_date(date_str=date_str)
            hour = get_hour_from_date(date_str=date_str)
            minute = get_minute_from_date(date_str=date_str)

            # Parse the full datetime string
            parsed_dt: datetime = date_parser.parse(date_str, fuzzy=False)

            # Create a unique key for deduplication
            dt_key = parsed_dt.isoformat() + date_str

            if dt_key not in seen_dates:
                seen_dates.add(dt_key)
                results.append({"datetime": parsed_dt, "original": date_str})
        except (ValueError, TypeError):
            continue  # Skip invalid or unparsable dates

    # Sort results by datetime
    results.sort(key=lambda x: x["datetime"])

    return results


@typechecked
def can_swap_day_and_month(*, some_date: datetime) -> bool:
    try:
        datetime(
            some_date.year,
            some_date.day,
            some_date.month,
            some_date.hour,
            some_date.minute,
            some_date.second,
        )
        return True
    except ValueError:
        return False


@typechecked
def swap_month_day(*, some_date: datetime) -> Optional[datetime]:
    if can_swap_day_and_month(some_date=some_date):
        return datetime(
            some_date.year,
            some_date.day,
            some_date.month,
            some_date.hour,
            some_date.minute,
            some_date.second,
        )
    else:
        raise ValueError(
            f"Should be able to swap day and month, got:{some_date}."
        )
