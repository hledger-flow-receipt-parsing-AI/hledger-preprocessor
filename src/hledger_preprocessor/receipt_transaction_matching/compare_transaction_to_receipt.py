import logging
from typing import List

from typeguard import typechecked

from hledger_preprocessor.TransactionObjects.Receipt import (
    AccountTransaction,
    ExchangedItem,
    Receipt,
)

logger = logging.getLogger(__name__)


@typechecked
def collect_account_transactions(
    receipt: Receipt,
    verbose: bool = False,
) -> List[AccountTransaction]:
    """Collect all account transactions from receipt's bought and returned items."""
    # Handle net_bought_items: convert to list if single item or None
    bought_items = (
        [receipt.net_bought_items]
        if isinstance(receipt.net_bought_items, ExchangedItem)
        else receipt.net_bought_items if receipt.net_bought_items else []
    )

    # Handle net_returned_items: convert to list if single item or None
    returned_items = (
        [receipt.net_returned_items]
        if isinstance(receipt.net_returned_items, ExchangedItem)
        else receipt.net_returned_items if receipt.net_returned_items else []
    )

    # Combine items and extract account transactions
    all_account_transactions = []
    for item in bought_items + returned_items:
        all_account_transactions.extend(item.account_transactions)

    if not all_account_transactions and verbose:
        print("No account transactions found in receipt.")

    if not all_account_transactions:
        raise ValueError("No account transactions found in receipt.")

    return all_account_transactions
