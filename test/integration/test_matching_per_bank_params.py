"""Integration tests for per-bank matching parameter overrides.

Covers US-1a.5: Per-bank matching params override global defaults.
"""

from copy import deepcopy

import pytest

from hledger_preprocessor.config.Config import Config
from hledger_preprocessor.config.load_config import load_config
from hledger_preprocessor.config.MatchingAlgoConfig import MatchingAlgoConfig
from hledger_preprocessor.matching.manual_actions.widen_amount_range import (
    widen_amount_range,
)
from hledger_preprocessor.matching.manual_actions.widen_date_range import (
    widen_date_range,
)


class TestPerBankDateOverride:
    """US-1a.5: Per-bank date margin can differ from global."""

    def test_widen_creates_independent_config(
        self, temp_finance_root
    ) -> None:
        """Widening for one bank creates a separate Config instance."""
        cfg = load_config(
            config_path=str(temp_finance_root["config_path"]),
            pre_processed_output_dir=None,
        )
        bank_cfg = widen_date_range(config=cfg, additional_days=3.0)

        # Bank has wider margin
        assert bank_cfg.matching_algo.days == cfg.matching_algo.days + 3.0
        # Global unchanged
        assert cfg.matching_algo.days == 2

    def test_successive_widenings_accumulate(
        self, temp_finance_root
    ) -> None:
        """Multiple widenings accumulate on the same config."""
        cfg = load_config(
            config_path=str(temp_finance_root["config_path"]),
            pre_processed_output_dir=None,
        )
        cfg1 = widen_date_range(config=cfg, additional_days=2.0)
        cfg2 = widen_date_range(config=cfg1, additional_days=3.0)
        assert cfg2.matching_algo.days == cfg.matching_algo.days + 5.0


class TestPerBankAmountOverride:
    """US-1a.5: Per-bank amount margin can differ from global."""

    def test_widen_amount_creates_independent_config(
        self, temp_finance_root
    ) -> None:
        """Widening amount for one bank creates a separate Config instance."""
        cfg = load_config(
            config_path=str(temp_finance_root["config_path"]),
            pre_processed_output_dir=None,
        )
        bank_cfg = widen_amount_range(
            config=cfg, abs_additive_widening_fraction=0.05
        )

        assert bank_cfg.matching_algo.amount_range == 0.05
        assert cfg.matching_algo.amount_range == 0

    def test_global_default_is_zero(
        self, temp_finance_root
    ) -> None:
        """Global default amount_range is 0 (exact match)."""
        cfg = load_config(
            config_path=str(temp_finance_root["config_path"]),
            pre_processed_output_dir=None,
        )
        assert cfg.matching_algo.amount_range == 0


class TestMatchingAlgoConfigIntegrity:
    """US-1a.5: MatchingAlgoConfig preserves all fields after override."""

    def test_days_month_swap_preserved(
        self, temp_finance_root
    ) -> None:
        """days_month_swap flag is preserved after widening."""
        cfg = load_config(
            config_path=str(temp_finance_root["config_path"]),
            pre_processed_output_dir=None,
        )
        original_swap = cfg.matching_algo.days_month_swap
        widened = widen_date_range(config=cfg, additional_days=5.0)
        assert widened.matching_algo.days_month_swap == original_swap

    def test_multiple_receipts_flag_preserved(
        self, temp_finance_root
    ) -> None:
        """multiple_receipts_per_transaction flag preserved after widening."""
        cfg = load_config(
            config_path=str(temp_finance_root["config_path"]),
            pre_processed_output_dir=None,
        )
        original_flag = cfg.matching_algo.multiple_receipts_per_transaction
        widened = widen_amount_range(
            config=cfg, abs_additive_widening_fraction=0.1
        )
        assert (
            widened.matching_algo.multiple_receipts_per_transaction
            == original_flag
        )
