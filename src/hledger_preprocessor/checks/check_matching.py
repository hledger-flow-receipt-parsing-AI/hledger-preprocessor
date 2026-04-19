"""Pre-flight matching check (US-4.7).

Reports which receipt transactions are still unlinked to CSV transactions,
before the interactive matching flow.  If unlabelled receipt images exist,
hints that the missing match may be there.
"""

import os
from decimal import Decimal
from typing import List

from typeguard import typechecked

from hledger_preprocessor.checks.unlabelled_receipts import (
    get_unlabelled_receipt_count,
)
from hledger_preprocessor.config.Config import Config
from hledger_preprocessor.generics.Transaction import Transaction
from hledger_preprocessor.receipt_transaction_matching.compare_transaction_to_receipt import (
    get_all_transactions_from_receipt,
)
from hledger_preprocessor.TransactionObjects.Receipt import Receipt


@typechecked
def check_matching(
    *,
    config: Config,
    labelled_receipts: List[Receipt],
) -> List[Transaction]:
    """Check which receipt transactions are still unlinked.

    Returns the list of unmatched transactions (AccountTransaction or
    GenericCsvTransaction) whose account has a CSV (i.e. where a match
    is expected).  Also prints a summary and, if unlabelled receipt
    images exist, a hint.
    """
    # Build set of accounts that have a CSV input.
    csv_accounts = set()
    for ac_cfg in config.accounts:
        if ac_cfg.has_input_csv():
            abs_csv = ac_cfg.get_abs_csv_filepath(
                dir_paths_config=config.dir_paths
            )
            if os.path.isfile(abs_csv):
                csv_accounts.add(
                    (
                        ac_cfg.account.account_holder,
                        ac_cfg.account.bank,
                        ac_cfg.account.account_type,
                    )
                )

    unmatched: List[Transaction] = []

    for receipt in labelled_receipts:
        all_txns = get_all_transactions_from_receipt(receipt=receipt)
        for txn in all_txns:
            acct_key = (
                txn.account.account_holder,
                txn.account.bank,
                txn.account.account_type,
            )
            # Only report unmatched if the account has a CSV to match against.
            if acct_key not in csv_accounts:
                continue
            if txn.original_transaction is None:
                unmatched.append(txn)

    # Print summary.
    if unmatched:
        print("")
        print("=" * 60)
        print(f"  {len(unmatched)} receipt transaction(s) not yet matched")
        print("=" * 60)
        for txn in unmatched:
            net = float(
                Decimal(str(txn.tendered_amount_out))
                - Decimal(str(txn.change_returned))
            )
            print(
                f"  {txn.the_date.strftime('%Y-%m-%d')}  "
                f"{net:>10.2f} {txn.account.base_currency.value}  "
                f"{txn.account.bank}:{txn.account.account_type}"
            )
        print("=" * 60)
    else:
        print("All receipt transactions are matched to CSV transactions.")

    # Hint about unlabelled images.
    unlabelled = get_unlabelled_receipt_count(config=config)
    if unlabelled > 0:
        print(
            f"\nNote: {unlabelled} receipt image(s) have no labels yet."
            " The missing match may be in one of them."
            "\nRun --tui-label-receipts to label them."
        )

    return unmatched
