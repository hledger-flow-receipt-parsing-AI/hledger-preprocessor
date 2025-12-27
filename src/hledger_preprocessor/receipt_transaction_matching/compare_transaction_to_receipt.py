import logging
from typing import List

from typeguard import typechecked

from hledger_preprocessor.generics.GenericTransactionWithCsv import (
    GenericCsvTransaction,
)
from hledger_preprocessor.TransactionObjects.Receipt import (
    AccountTransaction,
    ExchangedItem,
    Receipt,
)

logger = logging.getLogger(__name__)


@typechecked
def collect_non_csv_transactions(
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
    for x in bought_items:
        for transaction in x.account_transactions:
            if transaction.tendered_amount_out == -350:
                input(f" bought transaction={transaction}")

    # Handle net_returned_items: convert to list if single item or None
    returned_items = (
        [receipt.net_returned_items]
        if isinstance(receipt.net_returned_items, ExchangedItem)
        else receipt.net_returned_items if receipt.net_returned_items else []
    )

    for x in returned_items:
        for transaction in x.account_transactions:
            if transaction.tendered_amount_out == -350:
                input(f" returned_items transaction={transaction}")

    # Combine items and extract account transactions
    all_account_transactions: List[AccountTransaction] = []
    for item in bought_items + returned_items:
        for transaction in item.account_transactions:
            if transaction.tendered_amount_out == -350:
                input(f"transaction={transaction}")
            if isinstance(transaction, AccountTransaction):
                # all_account_transactions.extend(transaction)
                all_account_transactions.append(transaction)
            elif isinstance(transaction, GenericCsvTransaction):
                pass
            else:
                pass
    if not all_account_transactions and verbose:
        pass
    return all_account_transactions
