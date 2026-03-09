"""Integration tests for DD/MM day-month swap logic.

Covers US-3.5: Swap DD/MM — date 01-05-2025 wrong → swap → match.
"""

from datetime import datetime

import pytest

from hledger_preprocessor.date_extractor import (
    can_swap_day_and_month,
    is_within_date_range,
    swap_month_day,
)


class TestCanSwapDayAndMonth:
    """Test can_swap_day_and_month() predicate."""

    def test_swappable_date(self) -> None:
        """Jan 5 → May 1 (both valid dates)."""
        d = datetime(2025, 1, 5)
        assert can_swap_day_and_month(some_date=d) is True

    def test_not_swappable_high_day(self) -> None:
        """Jan 31 → month 31 is invalid."""
        d = datetime(2025, 1, 31)
        assert can_swap_day_and_month(some_date=d) is False

    def test_not_swappable_day_13(self) -> None:
        """Any month day=13 → month 13 is invalid."""
        d = datetime(2025, 3, 13)
        assert can_swap_day_and_month(some_date=d) is False

    def test_swappable_day_12(self) -> None:
        """Day 12 → month 12 (December) is valid."""
        d = datetime(2025, 3, 12)
        assert can_swap_day_and_month(some_date=d) is True

    def test_swappable_symmetric(self) -> None:
        """May 1 → Jan 5 swaps back."""
        d = datetime(2025, 5, 1)
        assert can_swap_day_and_month(some_date=d) is True


class TestSwapMonthDay:
    """Test swap_month_day() date transformation."""

    def test_swap_jan_5(self) -> None:
        """Jan 5 → May 1."""
        d = datetime(2025, 1, 5, 14, 30)
        swapped = swap_month_day(some_date=d)
        assert swapped.year == 2025
        assert swapped.month == 5
        assert swapped.day == 1
        assert swapped.hour == 14
        assert swapped.minute == 30

    def test_swap_mar_4(self) -> None:
        """Mar 4 → Apr 3."""
        d = datetime(2025, 3, 4)
        swapped = swap_month_day(some_date=d)
        assert swapped.month == 4
        assert swapped.day == 3

    def test_swap_is_involution(self) -> None:
        """Swapping twice returns the original date."""
        d = datetime(2025, 3, 7)
        swapped = swap_month_day(some_date=d)
        double_swapped = swap_month_day(some_date=swapped)
        assert d == double_swapped

    def test_swap_unswappable_raises(self) -> None:
        """Attempting to swap day=31 raises ValueError."""
        d = datetime(2025, 1, 31)
        with pytest.raises(ValueError):
            swap_month_day(some_date=d)


class TestSwapMatchingScenario:
    """US-3.5: Full scenario — receipt date 01-05-2025 interpreted as
    Jan 5 but actually May 1 → swap finds match."""

    def test_swap_resolves_ambiguous_date(self) -> None:
        """Receipt date Jan 5 doesn't match CSV Apr 30-May 2,
        but swapped (May 1) does."""
        receipt_date = datetime(2025, 1, 5)  # Parsed as Jan 5
        csv_date = datetime(2025, 5, 1)  # Actually May 1

        # Without swap: 116 days apart → no match within 2 days
        assert (
            is_within_date_range(a=receipt_date, b=csv_date, margin=2) is False
        )

        # After swap: Jan 5 → May 1 → exact match
        swapped = swap_month_day(some_date=receipt_date)
        assert is_within_date_range(a=swapped, b=csv_date, margin=2) is True

    def test_swap_not_needed_when_dates_close(self) -> None:
        """If dates are already close, swap is unnecessary."""
        receipt_date = datetime(2025, 3, 4)
        csv_date = datetime(2025, 3, 5)  # 1 day apart

        assert (
            is_within_date_range(a=receipt_date, b=csv_date, margin=2) is True
        )
