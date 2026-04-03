"""Merge multi-row CSV transactions that share a linking column value.

Exchanges like Kraken export trades as two separate ledger rows (spend + receive)
linked by a shared reference ID. This module merges those pairs into single
transactions matching the unified format (with quote_price, received_currency, etc.)
that exchanges like Bitvavo provide natively.
"""

from collections import OrderedDict
from typing import List, Tuple

from typeguard import typechecked

from hledger_preprocessor.config.CsvColumnMapping import CsvColumnMapping
from hledger_preprocessor.generics.GenericTransactionWithCsv import (
    GenericCsvTransaction,
)


@typechecked
def merge_linked_transactions(
    *,
    transactions: List[GenericCsvTransaction],
) -> List[GenericCsvTransaction]:
    """Group transactions by _merge_key and combine paired rows.

    Single-row groups pass through unchanged. Two-row groups (spend+receive)
    are merged into one unified transaction. Three+ row groups merge the
    first two and pass the rest through.
    """
    groups: OrderedDict[str, List[GenericCsvTransaction]] = OrderedDict()
    for txn in transactions:
        key = txn.extra.get("_merge_key", "")
        if not key:
            groups.setdefault("_no_key_" + str(id(txn)), []).append(txn)
            continue
        if key not in groups:
            groups[key] = []
        groups[key].append(txn)

    result: List[GenericCsvTransaction] = []
    for key, group in groups.items():
        if len(group) == 1:
            result.append(group[0])
        elif len(group) == 2:
            result.append(_merge_two_rows(group[0], group[1]))
        else:
            # 3+ rows with same key — merge first two, pass rest through
            result.append(_merge_two_rows(group[0], group[1]))
            for extra_txn in group[2:]:
                result.append(extra_txn)

    return result


@typechecked
def _identify_spend_receive(
    txn_a: GenericCsvTransaction,
    txn_b: GenericCsvTransaction,
) -> Tuple[GenericCsvTransaction, GenericCsvTransaction]:
    """Return (spend, receive) based on _row_type or amount signs."""
    type_a = txn_a.extra.get("_row_type", "")
    type_b = txn_b.extra.get("_row_type", "")

    if type_a == "spend" and type_b == "receive":
        return txn_a, txn_b
    if type_a == "receive" and type_b == "spend":
        return txn_b, txn_a

    # Fallback: positive tendered_amount_out = money going out = spend
    net_a = txn_a.tendered_amount_out - txn_a.change_returned
    net_b = txn_b.tendered_amount_out - txn_b.change_returned
    if net_a > 0 and net_b <= 0:
        return txn_a, txn_b
    if net_b > 0 and net_a <= 0:
        return txn_b, txn_a

    # Last resort: first is spend
    return txn_a, txn_b


@typechecked
def _build_merged_mapping(
    spend_mapping: CsvColumnMapping,
    receive_mapping: CsvColumnMapping,
) -> CsvColumnMapping:
    """Build a union mapping covering all columns from both groups.

    Starts with spend mapping, appends receive-only columns, then adds
    computed columns (quote_price, quote_currency) if not already present.
    """
    seen_hledger: set = set()
    merged_pairs: list = []

    for py_field, hledger_name in spend_mapping.csv_column_mapping:
        merged_pairs.append((py_field, hledger_name))
        if hledger_name:
            seen_hledger.add(hledger_name)

    for py_field, hledger_name in receive_mapping.csv_column_mapping:
        if hledger_name and hledger_name not in seen_hledger:
            merged_pairs.append((py_field, hledger_name))
            seen_hledger.add(hledger_name)

    # Add computed columns not in either mapping
    for py_field, hledger_name in [
        ("quote_price", "quote_price"),
        ("quote_cost", "quote_cost"),
        ("quote_currency", "quote_currency"),
        ("fee_currency", "fee_currency"),
    ]:
        if hledger_name not in seen_hledger:
            merged_pairs.append((py_field, hledger_name))

    return CsvColumnMapping(csv_column_mapping=tuple(merged_pairs))


@typechecked
def _merge_two_rows(
    txn_a: GenericCsvTransaction,
    txn_b: GenericCsvTransaction,
) -> GenericCsvTransaction:
    """Merge a spend+receive pair into a single unified transaction."""
    spend, receive = _identify_spend_receive(txn_a, txn_b)

    # Extract fields from spend side
    spend_amount = abs(spend.tendered_amount_out - spend.change_returned)
    spend_currency = spend.extra.get("payment_currency")
    if not spend_currency and spend.payment_currency:
        spend_currency = (
            spend.payment_currency.value
            if hasattr(spend.payment_currency, "value")
            else str(spend.payment_currency)
        )
    if not spend_currency:
        spend_currency = spend.account.base_currency.value
    fee_amount = spend.extra.get("fee_amount", 0.0) or 0.0
    fee_currency = spend.extra.get("fee_currency") or spend_currency

    # Extract fields from receive side
    received_amount = receive.extra.get("received_amount")
    if received_amount is None or received_amount == 0:
        # receive row may have amount in tendered_amount_out (negated)
        received_amount = abs(
            receive.tendered_amount_out - receive.change_returned
        )
    received_currency = (
        receive.extra.get("received_currency")
        or receive.extra.get("payment_currency")
    )
    if not received_currency and receive.payment_currency:
        received_currency = (
            receive.payment_currency.value
            if hasattr(receive.payment_currency, "value")
            else str(receive.payment_currency)
        )

    # If spend side has no fee, check receive side.
    if not fee_amount:
        receive_fee = receive.extra.get("fee_amount", 0.0) or 0.0
        if receive_fee:
            fee_amount = receive_fee
            fee_currency = (
                receive.extra.get("fee_currency")
                or received_currency
                or spend_currency
            )

    # Determine buy vs sell by comparing amounts.
    # Buy: spend_amount (fiat) > received_amount (crypto units) — e.g. 1800 EUR → 0.02 BTC
    # Sell: spend_amount (crypto units) < received_amount (fiat) — e.g. 0.02 BTC → 2017 USD
    is_buy = spend_amount > received_amount

    # Compute quote_price (per-unit, informational) and quote_cost (total,
    # used in @@ notation to avoid rounding errors).
    if received_amount and spend_amount:
        if is_buy:
            # Buy: crypto_cost = spend_amount (net, excluding fee)
            quote_price = spend_amount / received_amount
            quote_cost = spend_amount
        else:
            # Sell: crypto_cost = received_amount + fee_amount
            if fee_currency == received_currency:
                quote_cost = round(received_amount + fee_amount, 10)
            else:
                quote_cost = received_amount
            quote_price = quote_cost / spend_amount
    else:
        quote_price = 0.0
        quote_cost = 0.0

    # Build merged mapping from both groups
    spend_mapping = spend.extra.get("_csv_column_mapping")
    receive_mapping = receive.extra.get("_csv_column_mapping")
    merged_mapping = None
    if spend_mapping and receive_mapping:
        merged_mapping = _build_merged_mapping(spend_mapping, receive_mapping)
    elif spend_mapping:
        merged_mapping = spend_mapping

    # Build the merged transaction
    merged_extra = dict(spend.extra)
    merged_extra.update({
        "payment_currency": spend_currency,
        "quote_currency": spend_currency,
        "quote_price": quote_price,
        "quote_cost": quote_cost,
        "received_currency": received_currency,
        "received_amount": received_amount,
        "fee_currency": fee_currency,
        "fee_amount": fee_amount,
        "_row_type": "merged",
    })
    if merged_mapping:
        merged_extra["_csv_column_mapping"] = merged_mapping

    # For buys:  amount = spend + fee  (balance: cost + fee = amount)
    # For sells: amount = spend only  (balance: amount * qp = recv + fee)
    # Round to 10 decimal places to avoid float addition drift (e.g.
    # 251.12 + 3.77 = 254.89000000000001).
    total_out = round(
        spend_amount + fee_amount if is_buy else spend_amount, 10
    )

    return GenericCsvTransaction(
        account=spend.account,
        the_date=spend.the_date,
        tendered_amount_out=total_out,
        change_returned=0.0,
        description=spend.description or receive.description,
        # Leave payment_currency=None so to_hledger_dict() picks up the
        # (possibly swapped) value from extra["payment_currency"].
        payment_currency=None,
        extra=merged_extra,
    )
