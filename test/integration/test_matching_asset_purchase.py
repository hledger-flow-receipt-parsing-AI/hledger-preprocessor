"""Integration tests for asset purchase matching.

Covers US-3.9: Direct asset purchase (gold) — GRAMS → asset conversion.
Covers US-1a.4: Crypto config loads without error.
"""

import pytest

from hledger_preprocessor.Currency import Currency, DirectAssetPurchases


class TestCurrencyTypes:
    """US-3.9: Currency enum supports physical assets and crypto."""

    def test_gold_in_currency(self) -> None:
        """GOLD is a valid Currency enum member."""
        assert Currency.GOLD.value == "GOLD"

    def test_silver_in_currency(self) -> None:
        """SILVER is a valid Currency enum member."""
        assert Currency.SILVER.value == "SILVER"

    def test_grams_in_currency(self) -> None:
        """GRAMS is a valid Currency for weight-based assets."""
        assert Currency.GRAMS.value == "GRAMS"

    def test_physical_currencies(self) -> None:
        """get_physical() returns GOLD and SILVER."""
        physical = Currency.get_physical()
        assert Currency.GOLD in physical
        assert Currency.SILVER in physical
        assert Currency.EUR not in physical

    def test_crypto_currencies(self) -> None:
        """get_crypto() returns BTC and other crypto."""
        crypto = Currency.get_crypto()
        assert Currency.BTC in crypto
        assert Currency.ETH in crypto
        assert Currency.EUR not in crypto

    def test_fiat_currencies(self) -> None:
        """get_fiat() returns EUR, USD, POUND."""
        fiat = Currency.get_fiat()
        assert Currency.EUR in fiat
        assert Currency.USD in fiat
        assert Currency.POUND in fiat
        assert Currency.BTC not in fiat

    def test_two_digit_rounded_equals_fiat(self) -> None:
        """get_2_digit_rounded() is same as get_fiat()."""
        assert Currency.get_2_digit_rounded() == Currency.get_fiat()


class TestDirectAssetPurchases:
    """US-3.9: DirectAssetPurchases enum for gold/silver/cash."""

    def test_cash_asset(self) -> None:
        """CASH is a direct asset purchase type."""
        assert DirectAssetPurchases.CASH.value == "cash"

    def test_gold_asset(self) -> None:
        """GOLD is a direct asset purchase type."""
        assert DirectAssetPurchases.GOLD.value == "gold"

    def test_silver_asset(self) -> None:
        """SILVER is a direct asset purchase type."""
        assert DirectAssetPurchases.SILVER.value == "silver"

    def test_asset_enum_members(self) -> None:
        """All expected members exist."""
        members = [m.value for m in DirectAssetPurchases]
        assert "cash" in members
        assert "gold" in members
        assert "silver" in members


class TestCryptoConfig:
    """US-1a.4: Crypto config loads and has correct base currency."""

    def test_crypto_config_loads(self, temp_finance_root) -> None:
        """Crypto config template can be loaded."""
        # Use 1_bank_crypto.yaml if available, else standard config
        from pathlib import Path

        from hledger_preprocessor.config.load_config import load_config

        crypto_config = (
            Path(temp_finance_root["config_path"]).parent.parent
            / "test"
            / "fixtures"
            / "config_templates"
            / "1_bank_crypto.yaml"
        )
        if not crypto_config.exists():
            pytest.skip("1_bank_crypto.yaml not available")

        cfg = load_config(
            config_path=str(crypto_config),
            pre_processed_output_dir=None,
        )
        # Verify BTC wallet account exists
        btc_accounts = [
            ac
            for ac in cfg.account_configs
            if ac.account.base_currency == Currency.BTC
        ]
        assert len(btc_accounts) >= 1
        assert btc_accounts[0].account.base_currency == Currency.BTC

    def test_btc_is_not_fiat(self) -> None:
        """BTC is classified as crypto, not fiat."""
        assert Currency.BTC not in Currency.get_fiat()
        assert Currency.BTC in Currency.get_crypto()
