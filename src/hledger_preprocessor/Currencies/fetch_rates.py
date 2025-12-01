from datetime import datetime

import pandas as pd
import requests
from typeguard import typechecked

from hledger_preprocessor.config.load_config import Config, load_config
from hledger_preprocessor.Currency import Currency


@typechecked
def fetch_exchange_rates(*, base_currency: str = "EUR"):
    rates = {}
    sources = {}
    now = datetime.now().isoformat()

    # Define CoinGecko IDs for cryptocurrencies
    crypto_ids = {
        "BTC": "bitcoin",
        "XMR": "monero",
        "ZCASH": "zcash",
        "ETH": "ethereum",
        "WBTC": "wrapped-bitcoin",
        "LINK": "chainlink",
        "RVN": "ravencoin",
    }

    # Get fiat currencies: combine Enum fiat with dynamically fetched ones
    fiat_currencies = [c.value for c in Currency.get_fiat()]
    try:
        # Fetch supported currencies from Frankfurter API
        currencies_api = "https://api.frankfurter.app/currencies"
        response = requests.get(currencies_api)
        if response.status_code == 200:
            data = response.json()
            # Add all fiat currencies from API that aren't already in Enum
            api_fiat_currencies = list(data.keys())
            fiat_currencies = list(set(fiat_currencies + api_fiat_currencies))
    except Exception as e:
        print(f"Error fetching fiat currency list: {e}")

    # Get crypto currencies (all non-fiat, non-commodity currencies from Enum)
    crypto_currencies = [
        c.value
        for c in Currency
        if c not in Currency.get_fiat() and c.value not in ["GRAMS", "LITER"]
    ]

    # Fetch fiat currency rates using Frankfurter API
    try:
        fiat_api = f"https://api.frankfurter.app/latest?base={base_currency}"
        response = requests.get(fiat_api)
        if response.status_code == 200:
            data = response.json()
            if "rates" in data:
                for curr in fiat_currencies:
                    if curr != base_currency and curr in data["rates"]:
                        rates[curr] = data["rates"][curr]
                        sources[curr] = fiat_api
            else:
                print(f"Error: No 'rates' in Frankfurter API response: {data}")
    except Exception as e:
        print(f"Error fetching fiat rates: {e}")

    # Fetch crypto currency rates using CoinGecko
    try:
        crypto_api = "https://api.coingecko.com/api/v3/simple/price"
        params = {
            "ids": ",".join(
                [
                    crypto_ids.get(c, "")
                    for c in crypto_currencies
                    if crypto_ids.get(c)
                ]
            ),
            "vs_currencies": base_currency.lower(),
        }
        response = requests.get(crypto_api, params=params)
        if response.status_code == 200:
            data = response.json()
            for symbol, cg_id in crypto_ids.items():
                if cg_id in data and base_currency.lower() in data[cg_id]:
                    rates[symbol] = data[cg_id][base_currency.lower()]
                    sources[symbol] = crypto_api
    except Exception as e:
        print(f"Error fetching crypto rates: {e}")

    # Add base currency rate (always 1)
    rates[base_currency] = 1.0
    sources[base_currency] = "Base"

    # Store to CSV (append mode to keep history)
    df_rates = pd.DataFrame(
        {
            "datetime": [now] * len(rates),
            "source": list(sources.values()),
            "currency": list(rates.keys()),
            "rate_to_base": list(rates.values()),
        }
    )

    config: Config = load_config(
        config_path="/home/a/finance/config.yaml",
        pre_processed_output_dir="TODO: replace this with a decent solution",
    )
    csv_path = f"{config.get_working_subdir_path(assert_exists=True)}/exchange_rates.csv"

    df_rates.to_csv(
        csv_path,
        mode="a",
        header=not pd.io.common.file_exists(csv_path),
        index=False,
    )

    return rates, now
