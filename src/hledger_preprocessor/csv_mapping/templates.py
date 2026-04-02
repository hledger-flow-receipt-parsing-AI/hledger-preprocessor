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
    merge_column: Optional[int] = None  # 0-based, links multi-row transactions


# ── Bitvavo ────────────────────────────────────────────────────────
# Columns: Timezone, Date, Time, Type, Currency, Amount, Quote Currency, Quote Price, Received / Paid Currency, Received / Paid Amount, Fee currency, Fee amount, Status, Transaction ID, Address

_BITVAVO_GROUP0 = TemplateGroup(
    values=('sell',),
    column_mappings=[
        ("", ""),                            # 0: Timezone
        ("the_date_only", "date"),           # 1: Date
        ("the_time_only", "time"),           # 2: Time
        ("", ""),                            # 3: Type
        ("payment_currency", "base_currency"),    # 4: Currency
        ("negate:tendered_amount_out", "amount"), # 5: Amount
        ("quote_currency", "quote_currency"), # 6: Quote Currency
        ("quote_price", "quote_price"),      # 7: Quote Price
        ("received_currency", "received_currency"), # 8: Received / Paid Currency
        ("received_amount", "received_amount"), # 9: Received / Paid Amount
        ("fee_currency", "fee_currency"),    # 10: Fee currency
        ("fee_amount", "fee_amount"),        # 11: Fee amount
        ("", ""),                            # 12: Status
        ("description", "description"),      # 13: Transaction ID
        ("other_party_name", ""),            # 14: Address
    ],
)

_BITVAVO_GROUP1 = TemplateGroup(
    values=('buy',),
    column_mappings=[
        ("", ""),                            # 0: Timezone
        ("the_date_only", "date"),           # 1: Date
        ("the_time_only", "time"),           # 2: Time
        ("", ""),                            # 3: Type
        ("received_currency", "received_currency"), # 4: Currency
        ("received_amount", "received_amount"), # 5: Amount
        ("quote_currency", "quote_currency"), # 6: Quote Currency
        ("quote_price", "quote_price"),      # 7: Quote Price
        ("payment_currency", "base_currency"),    # 8: Received / Paid Currency
        ("negate:tendered_amount_out", "amount"), # 9: Received / Paid Amount
        ("fee_currency", "fee_currency"),    # 10: Fee currency
        ("fee_amount", "fee_amount"),        # 11: Fee amount
        ("", ""),                            # 12: Status
        ("description", "description"),      # 13: Transaction ID
        ("other_party_name", ""),            # 14: Address
    ],
)

_BITVAVO_GROUP2 = TemplateGroup(
    values=('campaign_new_user_incentive', 'rebate'),
    column_mappings=[
        ("", ""),                            # 0: Timezone
        ("the_date_only", "date"),           # 1: Date
        ("the_time_only", "time"),           # 2: Time
        ("description", "description"),      # 3: Type
        ("received_currency", "received_currency"), # 4: Currency
        ("received_amount", "received_amount"), # 5: Amount
        ("", ""),                            # 6: Quote Currency
        ("", ""),                            # 7: Quote Price
        ("payment_currency", "base_currency"),    # 8: Received / Paid Currency
        ("tendered_amount_out", "amount"),   # 9: Received / Paid Amount
        ("", ""),                            # 10: Fee currency
        ("", ""),                            # 11: Fee amount
        ("", ""),                            # 12: Status
        ("", ""),                            # 13: Transaction ID
        ("", ""),                            # 14: Address
    ],
)

_BITVAVO_GROUP3 = TemplateGroup(
    values=('deposit',),
    column_mappings=[
        ("", ""),                            # 0: Timezone
        ("the_date_only", "date"),           # 1: Date
        ("the_time_only", "time"),           # 2: Time
        ("", ""),                            # 3: Type
        ("received_currency", "received_currency"), # 4: Currency
        ("received_amount", "received_amount"), # 5: Amount
        ("", ""),                            # 6: Quote Currency
        ("", ""),                            # 7: Quote Price
        ("", ""),                            # 8: Received / Paid Currency
        ("", ""),                            # 9: Received / Paid Amount
        ("", ""),                            # 10: Fee currency
        ("", ""),                            # 11: Fee amount
        ("", ""),                            # 12: Status
        ("description", "description"),      # 13: Transaction ID
        ("other_party_name", ""),            # 14: Address
    ],
)

BITVAVO_TEMPLATE = CsvTemplate(
    name="Bitvavo",
    decimal_format="dot",
    split_column=3,
    groups=[_BITVAVO_GROUP0, _BITVAVO_GROUP1, _BITVAVO_GROUP2, _BITVAVO_GROUP3],
    detection_headers=frozenset({
        "Fee currency",
        "Quote Currency",
        "Quote Price",
        "Received / Paid Amount",
        "Received / Paid Currency",
    }),
)

# ── Kraken ─────────────────────────────────────────────────────────
# Columns: txid, refid, time, type, subtype, aclass, subclass, asset, wallet, amount, fee, balance

_KRAKEN_SPEND = TemplateGroup(
    values=('spend',),
    column_mappings=[
        ("", ""),                                # 0: txid
        ("description", "description"),          # 1: refid
        ("the_datetime", "date"),                # 2: time
        ("", ""),                                # 3: type
        ("", ""),                                # 4: subtype
        ("", ""),                                # 5: aclass
        ("", ""),                                # 6: subclass
        ("payment_currency", "base_currency"),   # 7: asset
        ("", ""),                                # 8: wallet
        ("negate:tendered_amount_out", "amount"),  # 9: amount
        ("fee_amount", "fee_amount"),            # 10: fee
        ("", ""),                                # 11: balance
    ],
)

_KRAKEN_RECEIVE = TemplateGroup(
    values=('receive',),
    column_mappings=[
        ("", ""),                                # 0: txid
        ("description", "description"),          # 1: refid
        ("the_datetime", "date"),                # 2: time
        ("", ""),                                # 3: type
        ("", ""),                                # 4: subtype
        ("", ""),                                # 5: aclass
        ("", ""),                                # 6: subclass
        ("received_currency", "received_currency"),  # 7: asset
        ("", ""),                                # 8: wallet
        ("received_amount", "received_amount"),  # 9: amount
        ("", ""),                                # 10: fee
        ("", ""),                                # 11: balance
    ],
)

_KRAKEN_DEPOSIT = TemplateGroup(
    values=('deposit',),
    column_mappings=[
        ("", ""),                                # 0: txid
        ("description", "description"),          # 1: refid
        ("the_datetime", "date"),                # 2: time
        ("", ""),                                # 3: type
        ("", ""),                                # 4: subtype
        ("", ""),                                # 5: aclass
        ("", ""),                                # 6: subclass
        ("received_currency", "received_currency"),  # 7: asset
        ("", ""),                                # 8: wallet
        ("received_amount", "received_amount"),  # 9: amount
        ("fee_amount", "fee_amount"),            # 10: fee
        ("", ""),                                # 11: balance
    ],
)

_KRAKEN_WITHDRAWAL = TemplateGroup(
    values=('withdrawal',),
    column_mappings=[
        ("", ""),                                # 0: txid
        ("description", "description"),          # 1: refid
        ("the_datetime", "date"),                # 2: time
        ("", ""),                                # 3: type
        ("", ""),                                # 4: subtype
        ("", ""),                                # 5: aclass
        ("", ""),                                # 6: subclass
        ("payment_currency", "base_currency"),   # 7: asset
        ("", ""),                                # 8: wallet
        ("negate:tendered_amount_out", "amount"),  # 9: amount
        ("fee_amount", "fee_amount"),            # 10: fee
        ("", ""),                                # 11: balance
    ],
)

KRAKEN_TEMPLATE = CsvTemplate(
    name="Kraken",
    decimal_format="dot",
    split_column=3,
    groups=[_KRAKEN_SPEND, _KRAKEN_RECEIVE, _KRAKEN_DEPOSIT, _KRAKEN_WITHDRAWAL],
    detection_headers=frozenset({
        "txid",
        "refid",
        "aclass",
        "subtype",
    }),
    merge_column=1,
)

# ── Registry ─────────────────────────────────────────────────────────

ALL_TEMPLATES: List[CsvTemplate] = [BITVAVO_TEMPLATE, KRAKEN_TEMPLATE]


def detect_template(headers: List[str]) -> Optional[CsvTemplate]:
    """Return the first template whose detection_headers all appear in headers."""
    header_set = set(h.strip() for h in headers)
    for template in ALL_TEMPLATES:
        if template.detection_headers.issubset(header_set):
            return template
    return None
