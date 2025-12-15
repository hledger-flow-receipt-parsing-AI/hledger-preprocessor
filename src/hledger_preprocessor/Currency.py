from enum import Enum
from typing import List

import pandas as pd
from typeguard import typechecked


class Currency(Enum):
    # Cryptocurrencies
    BTC = "BTC"
    XMR = "XMR"
    ZCASH = "ZCASH"
    ETH = "ETH"
    WBTC = "WBTC"
    LINK = "LINK"

    # ....coins
    RVN = "RVN"

    # Commodities
    GRAMS = "GRAMS"
    LITER = "LITER"

    # "Fiat"
    EUR = "EUR"
    USD = "USD"
    POUND = "POUND"

    GOLD = "GOLD"
    SILVER = "SILVER"

    @classmethod
    @typechecked
    def get_2_digit_rounded(cls) -> List["Currency"]:
        return cls.get_fiat()

    @classmethod
    @typechecked
    def get_fiat(cls) -> List["Currency"]:
        return [cls.EUR, cls.USD, cls.POUND]

    @classmethod
    @typechecked
    def get_crypto(cls) -> List["Currency"]:
        return [cls.BTC, cls.XMR, cls.ZCASH, cls.ETH, cls.WBTC, cls.LINK]

    @classmethod
    @typechecked
    def get_physical(cls) -> List["Currency"]:
        return [cls.SILVER, cls.GOLD]


class DirectAssetPurchases(Enum):
    CASH = "cash"
    GOLD = "gold"
    SILVER = "silver"
    # Add other asset categories as needed


# Function to load latest rates from CSV
def load_latest_rates(base_currency="EUR"):
    csv_path = "exchange_rates.csv"
    if not pd.io.common.file_exists(csv_path):
        return {}

    df = pd.read_csv(csv_path)
    df["datetime"] = pd.to_datetime(df["datetime"])
    # Get latest per currency
    latest = df.sort_values("datetime", ascending=False).drop_duplicates(
        "currency"
    )
    rates = dict(zip(latest["currency"], latest["rate_to_base"]))
    # Ensure base is 1
    rates[base_currency] = 1.0
    return rates
