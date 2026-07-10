"""Map a manifest's semantic ``script`` answers to concrete TUI inputs.

The manifest declares answers semantically (``account: {bank: triodos,
account_type: checking}``, ``currency: EUR``).  The urwid TUI, however, is
driven by positional indices.  This module resolves those indices
deterministically:

  * currency index  = position in the ``Currency`` enum (BTC=0 … EUR=9 …).
  * account index   = position of the matching account in the config's
                      ``account_configs`` order.

Both resolutions are self-checking: the run's produced label JSON is asserted
against the same semantic declaration (see ``expect:``), so a wrong index
surfaces immediately as a failing test rather than a silently wrong GIF.
"""

from __future__ import annotations

from typing import Any

import yaml

from .manifest import Manifest


def _date_digits(script: dict[str, Any]) -> str:
    """``2025-01-15`` + ``10:30`` -> ``202501151030`` (digits only)."""
    date = str(script["date"])
    time = str(script.get("time", "00:00"))
    return "".join(ch for ch in f"{date} {time}" if ch.isdigit())


def resolve_currency_index(currency: str) -> str:
    from hledger_core.Currency import Currency

    for i, c in enumerate(Currency):
        if c.name == currency:
            return str(i)
    raise ValueError(f"Unknown currency {currency!r}")


def resolve_account_index(account: dict[str, str], config_path: str) -> str:
    """Position of *account* (bank+account_type) in ``account_configs``."""
    config_dict = yaml.safe_load(open(config_path).read())
    accounts = config_dict.get("account_configs", [])
    for i, acc in enumerate(accounts):
        if (
            acc.get("bank") == account["bank"]
            and acc.get("account_type") == account["account_type"]
        ):
            return str(i)
    raise ValueError(
        f"Account {account} not found in {config_path} account_configs"
    )


def to_demo_values(manifest: Manifest, config_path: str):
    """Build a ``ReceiptDemoValues`` from *manifest* against *config_path*.

    Imported lazily so the manifest can be read without the gifs automation
    package (and its pexpect dep) being importable.
    """
    from gifs.automation.receipt_editor import ReceiptDemoValues

    s = manifest.script
    shop = s.get("shop", {})
    return ReceiptDemoValues(
        date_digits=_date_digits(s),
        is_withdrawal=bool(s.get("is_withdrawal", False)),
        category=str(s.get("category", "")),
        account_index=resolve_account_index(s["account"], config_path),
        currency_index=resolve_currency_index(s["currency"]),
        amount=str(s.get("amount", "")),
        change=str(s.get("change", "0")),
        add_another_account=bool(s.get("add_another_account", False)),
        shop_index="0",  # 0 = "manual address" (no history in a fresh run)
        shop_name=str(shop.get("name", "")),
        shop_street=str(shop.get("street", "")),
        shop_house_nr=str(shop.get("house_nr", "")),
        shop_zipcode=str(shop.get("zipcode", "")),
        shop_city=str(shop.get("city", "")),
        shop_country=str(shop.get("country", "")),
        subtotal=str(s.get("subtotal", "")),
        total_tax=str(s.get("total_tax", "")),
    )
