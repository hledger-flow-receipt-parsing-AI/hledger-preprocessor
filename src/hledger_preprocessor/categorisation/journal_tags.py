"""The tags a transaction carries into the journal, taken from its receipt.

A receipt's tags (events and projects such as "workbench") become hledger tags
on the transactions it paid with ("; workbench:"), so the journal and the
dashboard can add up what a project cost.  Its traceability goes along as
traceable:yes or traceable:no: what the user said ("traceable" or
"untraceable" among the tags), else yes when the receipt was paid partly
by card and partly in cash (the card payment ties the purchase to the
user), else nothing (the dashboard then decides by account).

A bank statement row is the transaction of a receipt when the receipt paid
from that bank account on the same day the same amount, and no other row
or receipt shares that.  (The stored link of a labelled card payment to its
statement row does not survive reading the label back, see
classify_transactions.)
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date
from typing import Any, Iterable, Tuple

from hledger_core.tagging import journal_comment, stated_traceability
from typeguard import typechecked

PaymentKey = Tuple[str, date, float]


@typechecked
def csv_account_names(*, config: Any) -> set[str]:
    """The accounts that come from a bank (or exchange) CSV: payments from
    them are on someone else's statement."""
    return {
        account_config.account.to_string()
        for account_config in getattr(config, "accounts", None) or []
        if account_config.has_input_csv()
    }


@typechecked
def _payments(*, receipt: Any) -> list[Any]:
    try:
        return list(receipt.get_both_item_types())
    except Exception:  # a receipt without items (partial or mock)
        return []


@typechecked
def payment_key(*, transaction: Any) -> PaymentKey | None:
    account = getattr(transaction, "account", None)
    when = getattr(transaction, "the_date", None)
    if account is None or when is None:
        return None
    paid = getattr(transaction, "tendered_amount_out", 0.0) or 0.0
    back = getattr(transaction, "change_returned", 0.0) or 0.0
    # Banks differ in sign: a statement may print a payment as -42.17.
    return (account.to_string(), when.date(), round(abs(paid - back), 2))


@typechecked
def paid_by_card_and_cash(*, receipt: Any, csv_accounts: set[str]) -> bool:
    accounts = {
        transaction.account.to_string()
        for transaction in _payments(receipt=receipt)
        if getattr(transaction, "account", None) is not None
    }
    return bool(accounts & csv_accounts) and bool(accounts - csv_accounts)


@typechecked
def receipt_journal_comment(*, receipt: Any, csv_accounts: set[str]) -> str:
    """The journal comment for the transactions of *receipt*."""
    tags: list[str] = list(getattr(receipt, "tags", None) or [])
    traceable = stated_traceability(tags=tags)
    if traceable is None and paid_by_card_and_cash(
        receipt=receipt, csv_accounts=csv_accounts
    ):
        traceable = True
    return journal_comment(tags=tags, traceable=traceable)


@typechecked
def duplicate_key(*, receipt: Any) -> tuple | None:
    """What two labels of the same receipt (two photos of it, labelled
    separately) have in common: the moment, the shop and every payment."""
    the_date = getattr(receipt, "the_date", None)
    if the_date is None:
        return None
    shop = getattr(getattr(receipt, "shop_identifier", None), "name", None)
    payments = sorted(
        key
        for key in (
            payment_key(transaction=t) for t in _payments(receipt=receipt)
        )
        if key is not None
    )
    if not payments:
        return None
    return (the_date, shop, tuple(payments))


@typechecked
def later_duplicates(*, receipts: Iterable[Any]) -> dict[int, Any]:
    """id() of every receipt that repeats an earlier one -> that earlier
    receipt.  The first label of a receipt is the one that counts."""
    first: dict[tuple, Any] = {}
    repeats: dict[int, Any] = {}
    for receipt in receipts:
        key = duplicate_key(receipt=receipt)
        if key is None:
            continue
        if key in first:
            repeats[id(receipt)] = first[key]
        else:
            first[key] = receipt
    return repeats


class ReceiptLinks:
    """The receipt of a bank statement row: the one receipt that paid from
    the row's account on its day the row's amount, when no other row of the
    statement has that day and amount too."""

    @typechecked
    def __init__(self, *, receipts: Iterable[Any], rows: Iterable[Any]) -> None:
        receipts = list(receipts)
        repeats = later_duplicates(receipts=receipts)
        self._receipts: dict[PaymentKey, list[Any]] = defaultdict(list)
        for receipt in receipts:
            if id(receipt) in repeats:
                continue  # a second label of a receipt already indexed
            for transaction in _payments(receipt=receipt):
                key = payment_key(transaction=transaction)
                if key is None:
                    continue
                if all(known is not receipt for known in self._receipts[key]):
                    self._receipts[key].append(receipt)
        self._rows: Counter = Counter(
            key
            for key in (payment_key(transaction=row) for row in rows)
            if key is not None
        )

    @typechecked
    def receipt_of(self, *, row: Any) -> Any | None:
        key = payment_key(transaction=row)
        if key is None or self._rows[key] != 1:
            return None
        found = self._receipts.get(key, [])
        return found[0] if len(found) == 1 else None
