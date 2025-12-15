import csv
import os
from pathlib import Path
from pprint import pprint
from typing import Dict, List, Optional

from typeguard import typechecked

from hledger_preprocessor.config.AccountConfig import AccountConfig
from hledger_preprocessor.csv_parsing.check_assets_in_csv_status import (
    classified_transaction_is_exported,
)
from hledger_preprocessor.csv_parsing.read_csv_asset_transactions import (
    read_csv_to_asset_transactions,
)
from hledger_preprocessor.generics.GenericTransactionWithCsv import (
    GenericCsvTransaction,
)
from hledger_preprocessor.generics.Transaction import Transaction
from hledger_preprocessor.TransactionObjects import AccountTransaction


@typechecked
def get_hledger_dict(
    *, transaction: Transaction, account_config: Optional[AccountConfig]
) -> Dict:
    if isinstance(transaction, GenericCsvTransaction):
        if not isinstance(account_config, AccountConfig):
            raise TypeError(
                "account_config was not of AccountConfig type. It"
                f" was:{account_config}"
            )
        hledger_tnx_dict: Dict = transaction.to_hledger_dict(
            csv_column_mapping=account_config.csv_column_mapping
        )
    else:
        hledger_tnx_dict: Dict = transaction.to_hledger_dict()
    if (
        list(hledger_tnx_dict.keys())
        != account_config.get_hledger_csv_column_names()
    ):
        raise ValueError(
            "Should be equal at all times:"
            f" {list(hledger_tnx_dict.keys())}!={account_config.get_hledger_csv_column_names()}"
        )
    return hledger_tnx_dict


@typechecked
def assert_uniform_tnx_types(*, tnx: List[Transaction]) -> None:
    if not tnx:
        return
    expected_type = type(tnx[0])
    for t in tnx:
        if type(t) is not expected_type:
            raise TypeError(
                "All transactions must be of the same type. Expected"
                f" {expected_type}, but found {type(t)} in list {tnx}"
            )

    transaction = tnx[0]
    if isinstance(transaction, GenericCsvTransaction):
        return
    elif isinstance(transaction, AccountTransaction):
        return
    else:
        raise TypeError(
            f"Did not expected tnx of type:{type(transaction)}for {tnx}"
        )


@typechecked
def write_processed_csv(
    *,
    transactions: List[Transaction],
    account_config: AccountConfig,
    filepath: str,
) -> None:
    # Get fieldnames dynamically from the first object in the list
    if transactions:
        assert_uniform_tnx_types(tnx=transactions)
        hledger_tnx_dicts: List[Dict] = []
        for txn in transactions:
            if isinstance(txn, GenericCsvTransaction):
                hledger_tnx_dict: Dict = get_hledger_dict(
                    transaction=txn, account_config=account_config
                )
            else:
                hledger_tnx_dict: Dict = get_hledger_dict(
                    transaction=txn, account_config=None
                )
        hledger_tnx_dicts.append(hledger_tnx_dict)
        assert all(
            d.keys() == hledger_tnx_dicts[0].keys() for d in hledger_tnx_dicts
        ), "All hledger dicts must have identical keys!"

        with open(filepath, mode="w", encoding="utf-8", newline="") as outfile:
            writer = csv.DictWriter(
                outfile,
                fieldnames=hledger_tnx_dicts[0].keys(),
                quoting=csv.QUOTE_ALL,
            )
            writer.writeheader()

            # Write each transaction as a row in the CSV
            for hledger_tnx_dict in hledger_tnx_dicts:
                writer.writerow(hledger_tnx_dict)


@typechecked
def write_asset_transaction_to_csv(
    transaction: AccountTransaction,
    filepath: str,
    account_config: AccountConfig,
    csv_encoding: str = "utf-8",  # Added encoding parameter for consistency
) -> None:
    """
    Export a single AccountTransaction to a CSV file.
    - Checks if the transaction is already in the file (raises ValueError if it is).
    - Appends the transaction if it is not present.
    - Asserts that the transaction was successfully added.

    Args:
        transaction: The AccountTransaction to export.
        filepath: The path to the CSV file.
        csv_encoding: The encoding to use for reading/writing the CSV file (default: utf-8).

    Raises:
        ValueError: If the transaction is already in the CSV file.
    """

    # Convert transaction to dictionary for comparison and writing
    txn_dict = transaction.to_hledger_dict()
    print(f"asset txn_dict={txn_dict}")
    if not classified_transaction_is_exported(
        asset_transaction=transaction,
        csv_output_filepath=filepath,
        csv_encoding=csv_encoding,
    ):

        # Ensure the directory exists
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)

        # Now it's safe to open/append
        with open(
            filepath, mode="a", encoding=csv_encoding, newline=""
        ) as outfile:
            writer = csv.DictWriter(
                outfile, fieldnames=list(txn_dict.keys()), quoting=csv.QUOTE_ALL
            )

            # Write header only if file is empty or newly created
            file_is_new = (
                not os.path.exists(filepath) or os.path.getsize(filepath) == 0
            )
            if file_is_new:
                writer.writeheader()
            writer.writerow(txn_dict)

        # Assert that the transaction was added
        if not classified_transaction_is_exported(
            asset_transaction=transaction,
            csv_output_filepath=filepath,
            csv_encoding=csv_encoding,
        ):
            csv_asset_transactions: List[AccountTransaction] = (
                read_csv_to_asset_transactions(
                    csv_filepath=filepath,
                    csv_encoding=csv_encoding,
                )
            )
            pprint("csv_asset_transactions=")
            pprint(csv_asset_transactions)
            raise AssertionError(
                f"Failed to verify transaction in \n{filepath}:"
                f" with:\n{txn_dict}"
            )

    else:
        raise ValueError(
            f"Transaction already exists in {filepath}: {txn_dict}"
        )
