"""Cross-validate inter-account transfers before processing.

After all CSVs are parsed but before classification/export, this module
checks that transfers between linked accounts have matching counterpart
transactions.  Matched transactions on the *current* account side are
suppressed (the other account's CSV already captures them).
"""

from datetime import timedelta
from typing import Dict, List, Set, Tuple

from typeguard import typechecked

from hledger_preprocessor.config.AccountConfig import AccountConfig, LinkedAccount
from hledger_preprocessor.generics.GenericTransactionWithCsv import (
    GenericCsvTransaction,
)

# Fiat currencies for which a missing counterpart is an error
_FIAT_CURRENCIES = {"EUR", "USD", "GBP", "CHF", "SEK", "NOK", "DKK", "PLN", "CZK"}

# Matching tolerances
_AMOUNT_TOLERANCE = 0.01
_DATE_TOLERANCE = timedelta(days=2)


@typechecked
def reconcile_linked_accounts(
    *,
    transactions_per_account: Dict[AccountConfig, List[GenericCsvTransaction]],
) -> Dict[AccountConfig, Set[int]]:
    """Identify transactions to suppress due to linked-account overlap.

    Returns a dict mapping each AccountConfig to a set of transaction
    indices (within its list) that should be suppressed.

    Raises ValueError when a fiat transfer has no matching counterpart.
    """
    suppressed: Dict[AccountConfig, Set[int]] = {
        ac: set() for ac in transactions_per_account
    }

    # Build account_id → (AccountConfig, transactions) lookup
    id_to_data: Dict[str, Tuple[AccountConfig, List[GenericCsvTransaction]]] = {}
    for ac, txns in transactions_per_account.items():
        acct = ac.account
        acct_id = f"{acct.account_holder}:{acct.bank}:{acct.account_type}"
        id_to_data[acct_id] = (ac, txns)

    for ac, txns in transactions_per_account.items():
        if not ac.linked_accounts:
            continue

        for linked in ac.linked_accounts:
            if not linked.transfer_types:
                continue

            linked_id = (
                f"{linked.account_holder}:{linked.bank}:{linked.account_type}"
            )
            linked_data = id_to_data.get(linked_id)
            if linked_data is None:
                acct = ac.account
                acct_id = f"{acct.account_holder}:{acct.bank}:{acct.account_type}"
                raise ValueError(
                    f"Account {linked_id} is declared as linked to "
                    f"{acct_id} but has no CSV config. Configure it first."
                )

            linked_ac, linked_txns = linked_data

            # Find transactions whose split-group type matches transfer_types
            for idx, txn in enumerate(txns):
                if idx in suppressed[ac]:
                    continue

                # Determine the row type from the extra dict
                row_type = txn.extra.get("_row_type", "")
                if row_type not in linked.transfer_types:
                    continue

                currency = _get_currency(txn)
                amount = abs(txn.tendered_amount_out)
                txn_date = txn.the_date

                # Search linked account for a matching transaction
                match_found = False
                for l_idx, l_txn in enumerate(linked_txns):
                    if l_idx in suppressed[linked_ac]:
                        continue

                    l_currency = _get_currency(l_txn)
                    l_amount = abs(l_txn.tendered_amount_out)
                    l_date = l_txn.the_date

                    if (
                        l_currency == currency
                        and abs(l_amount - amount) <= _AMOUNT_TOLERANCE
                        and abs((l_date - txn_date).total_seconds())
                        <= _DATE_TOLERANCE.total_seconds()
                    ):
                        match_found = True
                        suppressed[ac].add(idx)
                        break

                if not match_found:
                    if currency.upper() in _FIAT_CURRENCIES:
                        acct = ac.account
                        acct_id = (
                            f"{acct.account_holder}:{acct.bank}"
                            f":{acct.account_type}"
                        )
                        date_str = txn_date.strftime("%Y-%m-%d")
                        raise ValueError(
                            f"{acct_id} {row_type} of "
                            f"{currency} {amount:.2f} on {date_str} "
                            f"has no matching {linked_id} transaction. "
                            f"Ensure the {linked_id} CSV covers this "
                            f"date range."
                        )
                    # Crypto with no match: keep it (external wallet transfer)

    return suppressed


def _get_currency(txn: GenericCsvTransaction) -> str:
    """Extract currency string from a transaction."""
    if hasattr(txn, "payment_currency") and txn.payment_currency:
        return str(txn.payment_currency)
    return txn.extra.get("payment_currency", "")
