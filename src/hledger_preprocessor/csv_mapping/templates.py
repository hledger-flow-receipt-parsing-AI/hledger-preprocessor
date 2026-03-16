"""Pre-defined CSV column mapping templates for common exchanges/banks.

Templates provide auto-detection from CSV headers and pre-filled mappings
(optionally with split-by-type groups).
"""

from dataclasses import dataclass
from typing import FrozenSet, List, Optional, Tuple


@dataclass(frozen=True)
class TemplateGroup:
    """One group within a split-by-type template."""
    values: Tuple[str, ...]
    # (field_name_or_empty, hledger_name) per CSV column
    column_mappings: List[Tuple[Optional[str], str]]


@dataclass(frozen=True)
class CsvTemplate:
    name: str
    decimal_format: str  # "eu" or "dot"
    split_column: Optional[int]  # 0-based, or None if no split
    groups: List[TemplateGroup]
    detection_headers: FrozenSet[str]


# ── Bitvavo ──────────────────────────────────────────────────────────
# Columns: Timezone, Date, Time, Type, Currency, Amount,
#          Quote Currency, Quote Price, Received / Paid Currency,
#          Received / Paid Amount, Fee currency, Fee amount,
#          Status, Transaction ID, Address

_BITVAVO_DEPOSITS = TemplateGroup(
    values=("deposit", "rebate", "campaign_new_user_incentive"),
    column_mappings=[
        ("", ""),                                      # 0: Timezone
        ("the_date_only", "date"),                     # 1: Date
        ("the_time_only", "time"),                     # 2: Time
        ("", ""),                                      # 3: Type
        ("payment_currency", "currency"),              # 4: Currency
        ("tendered_amount_out", "amount"),              # 5: Amount
        ("", ""),                                      # 6: Quote Currency
        ("", ""),                                      # 7: Quote Price
        ("", ""),                                      # 8: Received / Paid Currency
        ("", ""),                                      # 9: Received / Paid Amount
        ("fee_currency", ""),                          # 10: Fee currency
        ("fee_amount", ""),                            # 11: Fee amount
        ("", ""),                                      # 12: Status
        ("description", "description"),                # 13: Transaction ID
        ("", ""),                                      # 14: Address
    ],
)

_BITVAVO_TRADES = TemplateGroup(
    values=("buy", "sell"),
    column_mappings=[
        ("", ""),                                      # 0: Timezone
        ("the_date_only", "date"),                     # 1: Date
        ("the_time_only", "time"),                     # 2: Time
        ("", ""),                                      # 3: Type
        ("payment_currency", "currency"),              # 4: Currency
        ("tendered_amount_out", "amount"),              # 5: Amount
        ("quote_currency", ""),                        # 6: Quote Currency
        ("quote_price", ""),                           # 7: Quote Price
        ("received_currency", ""),                     # 8: Received / Paid Currency
        ("received_amount", ""),                       # 9: Received / Paid Amount
        ("fee_currency", ""),                          # 10: Fee currency
        ("fee_amount", ""),                            # 11: Fee amount
        ("", ""),                                      # 12: Status
        ("description", "description"),                # 13: Transaction ID
        ("", ""),                                      # 14: Address
    ],
)

BITVAVO_TEMPLATE = CsvTemplate(
    name="Bitvavo",
    decimal_format="dot",
    split_column=3,
    groups=[_BITVAVO_DEPOSITS, _BITVAVO_TRADES],
    detection_headers=frozenset({
        "Quote Currency",
        "Quote Price",
        "Fee currency",
        "Received / Paid Currency",
        "Received / Paid Amount",
    }),
)

# ── Registry ─────────────────────────────────────────────────────────

ALL_TEMPLATES: List[CsvTemplate] = [BITVAVO_TEMPLATE]


def detect_template(headers: List[str]) -> Optional[CsvTemplate]:
    """Return the first template whose detection_headers all appear in headers."""
    header_set = set(h.strip() for h in headers)
    for template in ALL_TEMPLATES:
        if template.detection_headers.issubset(header_set):
            return template
    return None
