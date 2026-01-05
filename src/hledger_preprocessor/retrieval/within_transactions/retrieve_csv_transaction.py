from typing import Dict, List

from typeguard import typechecked

from hledger_preprocessor.config.AccountConfig import AccountConfig
from hledger_preprocessor.config.load_config import Config
from hledger_preprocessor.csv_parsing.csv_to_transactions import (
    load_csv_transactions_from_file_per_year,
)
from hledger_preprocessor.generics.Transaction import Transaction
from hledger_preprocessor.TransactionObjects.Receipt import Receipt


@typechecked
def retrieve_csv_transaction_from_hash(
    *, config: Config, some_hash: int, labelled_receipts: List[Receipt]
) -> Transaction:

    matching_transactions: List[Transaction] = get_all_matching_transactions(
        config=config, some_hash=some_hash, labelled_receipts=labelled_receipts
    )
    print(f"some_hash={some_hash}")
    input(f"matching_transactions={matching_transactions[0]}")
    if len(matching_transactions) == 1:
        return matching_transactions[0]
    elif len(matching_transactions) == 0:
        raise ValueError(f"Did not find transaction with hash:{some_hash}")
    else:
        raise ValueError(
            f"HASH COLLISION on: {some_hash} CHANGE YOUR HASHING METHOD!"
        )


@typechecked
def get_all_matching_transactions(
    *, config: Config, labelled_receipts: List[Receipt], some_hash: int
) -> List[Transaction]:
    matching_transactions: List[Transaction] = []
    transactions: Dict[AccountConfig, Dict[int, List[Transaction]]] = (
        get_all_transactions(
            config=config,
            labelled_receipts=labelled_receipts,
        )
    )
    # Loop over them.
    for (
        account_config,
        transactions_per_year_per_account,
    ) in transactions.items():
        for (
            year,
            yearly_transactions,
        ) in transactions_per_year_per_account.items():
            for some_transaction in yearly_transactions:
                if some_transaction.get_hash() == some_hash:
                    # Add all transactions that match the hash to the list.
                    matching_transactions.append(some_transaction)
    return matching_transactions


@typechecked
def get_all_transactions(
    config: Config, labelled_receipts: List[Receipt]
) -> Dict[AccountConfig, Dict[int, List[Transaction]]]:
    transactions: Dict[AccountConfig, Dict[int, List[Transaction]]] = {}
    # Load all csv_transactions.
    for account_config in config.accounts:

        transactions_per_year_per_account: Dict[int, List[Transaction]] = (
            load_csv_transactions_from_file_per_year(
                config=config,
                labelled_receipts=labelled_receipts,
                abs_csv_filepath=account_config.get_abs_csv_filepath(
                    dir_paths_config=config.dir_paths
                ),
                account_config=account_config,
                csv_encoding=config.csv_encoding,
            )
        )
        if account_config not in transactions.keys():
            transactions[account_config] = transactions_per_year_per_account
        else:
            raise KeyError(
                f"{account_config} already in transactions:{transactions}"
            )
    return transactions
