"""Integration tests for widening amount range in matching.

Covers US-3.4: Widen amount range — receipt 49.99, CSV 50.00 →
no exact match → widen ±0.02 → match.
"""

import pytest

from hledger_preprocessor.matching.searching.helper import (
    is_amount_within_margin,
)


class TestWidenAmountRange:
    """US-3.4: Widen amount tolerance to catch bank rounding."""

    def test_exact_match_zero_margin(self) -> None:
        """Zero margin requires exact match."""
        assert is_amount_within_margin(
            transaction_amount=49.99,
            receipt_amount=49.99,
            margin=0.0,
        ) is True

    def test_small_diff_fails_zero_margin(self) -> None:
        """50.00 vs 49.99 fails with zero margin."""
        assert is_amount_within_margin(
            transaction_amount=50.00,
            receipt_amount=49.99,
            margin=0.0,
        ) is False

    def test_small_diff_passes_with_margin(self) -> None:
        """50.00 vs 49.99 passes with 0.02 margin.
        diff=0.01, threshold=0.02*49.99=1.00 → match.
        """
        assert is_amount_within_margin(
            transaction_amount=50.00,
            receipt_amount=49.99,
            margin=0.02,
        ) is True

    def test_large_diff_still_fails(self) -> None:
        """55.00 vs 49.99 fails even with 0.02 margin.
        diff=5.01, threshold=0.02*49.99=1.00 → no match.
        """
        assert is_amount_within_margin(
            transaction_amount=55.00,
            receipt_amount=49.99,
            margin=0.02,
        ) is False

    def test_symmetric_margin(self) -> None:
        """Margin works in both directions."""
        margin = 0.01
        # Below receipt
        assert is_amount_within_margin(
            transaction_amount=49.50,
            receipt_amount=50.00,
            margin=margin,
        ) is True  # diff=0.50, threshold=0.01*50=0.50
        # Above receipt
        assert is_amount_within_margin(
            transaction_amount=50.50,
            receipt_amount=50.00,
            margin=margin,
        ) is True  # diff=0.50, threshold=0.01*50=0.50

    def test_progressive_widening(self) -> None:
        """Simulates widening: 0% → 1% → 2% → 5%."""
        txn_amount = 50.30
        receipt_amount = 50.00

        # 0%: diff=0.30 > 0 → no match
        assert (
            is_amount_within_margin(
                transaction_amount=txn_amount,
                receipt_amount=receipt_amount,
                margin=0.0,
            )
            is False
        )

        # 1%: diff=0.30, threshold=0.01*50=0.50 → match
        assert (
            is_amount_within_margin(
                transaction_amount=txn_amount,
                receipt_amount=receipt_amount,
                margin=0.01,
            )
            is True
        )
