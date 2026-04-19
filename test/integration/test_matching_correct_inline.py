"""Integration tests for correct-receipt-inline retry matching.

Covers US-3.8: Correct receipt inline — matcher retries with updated data.
"""

import pytest

from hledger_preprocessor.config.load_config import load_config
from hledger_preprocessor.matching.manual_actions.widen_amount_range import (
    widen_amount_range,
)
from hledger_preprocessor.matching.manual_actions.widen_date_range import (
    widen_date_range,
)


class TestCorrectInlineWidenDate:
    """US-3.8: Widen date range returns a new Config with updated days."""

    def test_widen_date_range_increases_days(self, temp_finance_root) -> None:
        """Widening by 3 days adds to existing margin."""
        cfg = load_config(
            config_path=str(temp_finance_root["config_path"]),
            pre_processed_output_dir=None,
        )
        original_days = cfg.matching_algo.days
        updated = widen_date_range(config=cfg, additional_days=3.0)
        assert updated.matching_algo.days == original_days + 3.0

    def test_widen_date_range_preserves_original(
        self, temp_finance_root
    ) -> None:
        """Original config is not mutated (deepcopy)."""
        cfg = load_config(
            config_path=str(temp_finance_root["config_path"]),
            pre_processed_output_dir=None,
        )
        original_days = cfg.matching_algo.days
        _ = widen_date_range(config=cfg, additional_days=5.0)
        assert cfg.matching_algo.days == original_days

    def test_widen_date_range_rejects_zero(self, temp_finance_root) -> None:
        """Zero additional_days raises ValueError."""
        cfg = load_config(
            config_path=str(temp_finance_root["config_path"]),
            pre_processed_output_dir=None,
        )
        with pytest.raises(ValueError, match="Negative/zero"):
            widen_date_range(config=cfg, additional_days=0.0)

    def test_widen_date_range_rejects_negative(self, temp_finance_root) -> None:
        """Negative additional_days raises ValueError."""
        cfg = load_config(
            config_path=str(temp_finance_root["config_path"]),
            pre_processed_output_dir=None,
        )
        with pytest.raises(ValueError, match="Negative/zero"):
            widen_date_range(config=cfg, additional_days=-1.0)


class TestCorrectInlineWidenAmount:
    """US-3.8: Widen amount range returns a new Config with updated range."""

    def test_widen_amount_from_zero(self, temp_finance_root) -> None:
        """Widening from 0 sets the fraction directly."""
        cfg = load_config(
            config_path=str(temp_finance_root["config_path"]),
            pre_processed_output_dir=None,
        )
        assert cfg.matching_algo.amount_range == 0
        updated = widen_amount_range(
            config=cfg, abs_additive_widening_fraction=0.05
        )
        assert updated.matching_algo.amount_range == 0.05

    def test_widen_amount_from_positive(self, temp_finance_root) -> None:
        """Widening from positive adds to existing range."""
        cfg = load_config(
            config_path=str(temp_finance_root["config_path"]),
            pre_processed_output_dir=None,
        )
        # First widen to get a positive amount_range
        cfg1 = widen_amount_range(
            config=cfg, abs_additive_widening_fraction=0.02
        )
        assert cfg1.matching_algo.amount_range == 0.02
        # Second widen adds to it
        cfg2 = widen_amount_range(
            config=cfg1, abs_additive_widening_fraction=0.03
        )
        assert abs(cfg2.matching_algo.amount_range - 0.05) < 1e-9

    def test_widen_amount_preserves_original(self, temp_finance_root) -> None:
        """Original config is not mutated (deepcopy)."""
        cfg = load_config(
            config_path=str(temp_finance_root["config_path"]),
            pre_processed_output_dir=None,
        )
        original_range = cfg.matching_algo.amount_range
        _ = widen_amount_range(config=cfg, abs_additive_widening_fraction=0.1)
        assert cfg.matching_algo.amount_range == original_range
