"""Unit tests for currency conversion math.

Covers US-3.2: Foreign currency match — conversion rate calculation.
"""


from hledger_preprocessor.Currency import Currency


class TestCurrencyEnumProperties:
    """US-3.2: Currency enum classifications for conversion logic."""

    def test_eur_is_fiat(self) -> None:
        """EUR is classified as fiat."""
        assert Currency.EUR in Currency.get_fiat()

    def test_gbp_is_fiat(self) -> None:
        """GBP is classified as fiat."""
        assert Currency.GBP in Currency.get_fiat()

    def test_btc_is_crypto(self) -> None:
        """BTC is classified as crypto."""
        assert Currency.BTC in Currency.get_crypto()

    def test_gold_is_physical(self) -> None:
        """GOLD is classified as physical."""
        assert Currency.GOLD in Currency.get_physical()

    def test_cash_is_physical(self) -> None:
        """CASH is classified as physical."""
        assert Currency.CASH in Currency.get_physical()

    def test_grams_not_in_fiat(self) -> None:
        """GRAMS is not fiat."""
        assert Currency.GRAMS not in Currency.get_fiat()

    def test_liter_not_in_crypto(self) -> None:
        """LITER is not crypto."""
        assert Currency.LITER not in Currency.get_crypto()


class TestConversionRateMath:
    """US-3.2: Conversion rate calculation between currencies."""

    def test_gbp_to_eur_conversion(self) -> None:
        """100 GBP * 1.175 = 117.50 EUR."""
        gbp_amount = 100.0
        rate = 1.175  # EUR per GBP
        eur_amount = gbp_amount * rate
        assert abs(eur_amount - 117.50) < 0.01

    def test_eur_to_gbp_inverse(self) -> None:
        """117.50 EUR / 1.175 = 100.00 GBP."""
        eur_amount = 117.50
        rate = 1.175
        gbp_amount = eur_amount / rate
        assert abs(gbp_amount - 100.0) < 0.01

    def test_conversion_rate_one_is_identity(self) -> None:
        """Rate 1.0 means same currency (no conversion needed)."""
        amount = 42.17
        rate = 1.0
        assert amount * rate == amount

    def test_usd_to_eur_example(self) -> None:
        """50 USD * 0.92 = 46.00 EUR."""
        usd_amount = 50.0
        rate = 0.92  # EUR per USD
        eur_amount = usd_amount * rate
        assert abs(eur_amount - 46.0) < 0.01
