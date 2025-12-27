import csv
import os
from datetime import datetime
from pathlib import Path
from pprint import pprint
from typing import Dict, List, Union

from typeguard import typechecked

from hledger_preprocessor.config.AccountConfig import AccountConfig
from hledger_preprocessor.config.Config import Config
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
from hledger_preprocessor.TransactionObjects.AccountTransaction import (
    AccountTransaction,
)
from hledger_preprocessor.TransactionObjects.ProcessedTransaction import (
    ProcessedTransaction,
)
from hledger_preprocessor.TransactionObjects.Receipt import Receipt


@typechecked
def assert_uniform_tnx_types(
    *, processed_txns: List[ProcessedTransaction]
) -> None:
    if not processed_txns:
        return
    transactions: List[Transaction] = list(
        map(lambda processed_tnx: processed_tnx.transaction, processed_txns)
    )
    expected_type = type(transactions[0])
    for t in transactions:
        if type(t) is not expected_type:
            raise TypeError(
                "All transactions must be of the same type. Expected"
                f" {expected_type}, but found {type(t)} in list {transactions}"
            )

    transaction = transactions[0]
    if isinstance(transaction, GenericCsvTransaction):
        return
    elif isinstance(transaction, AccountTransaction):
        return
    else:
        raise TypeError(
            f"Did not expected tnx of type:{type(transaction)}for"
            f" {transactions}"
        )


@typechecked
def write_processed_csv(
    *,
    processed_txns: List[ProcessedTransaction],
    account_config: AccountConfig,
    filepath: str,
) -> None:
    # Get fieldnames dynamically from the first object in the list
    if processed_txns:
        assert_uniform_tnx_types(processed_txns=processed_txns)
        hledger_tnx_dicts: List[
            Dict[str, Union[int, float, str, datetime, None]]
        ] = []

        for processed_tnx in processed_txns:
            hledger_dict: Dict[str, Union[int, float, str, datetime, None]] = (
                processed_tnx.to_hledger_dict(account_config=account_config)
            )
            # if isinstance(processed_tnx.transaction, GenericCsvTransaction):
            #     hledger_tnx_dict: Dict = get_hledger_dict(
            #         transaction=processed_tnx.transaction, account_config=account_config
            #     )
            # else:
            #     hledger_tnx_dict: Dict = get_hledger_dict(
            #         transaction=processed_tnx.transaction, account_config=None
            #     )
            hledger_tnx_dicts.append(hledger_dict)
            assert all(
                d.keys() == hledger_tnx_dicts[0].keys()
                for d in hledger_tnx_dicts
            ), "All hledger dicts must have identical keys!"

        with open(filepath, mode="w", encoding="utf-8", newline="") as outfile:
            writer = csv.DictWriter(
                outfile,
                fieldnames=hledger_tnx_dicts[0].keys(),
                quoting=csv.QUOTE_ALL,
            )
            writer.writeheader()

            # Write each transaction as a row in the CSV
            for i, hledger_tnx_dict in enumerate(hledger_tnx_dicts):
                # print(f"writing line:{i}={hledger_tnx_dict}")
                writer.writerow(hledger_tnx_dict)


@typechecked
def write_asset_transaction_to_csv(
    config: Config,
    labelled_receipts: List[Receipt],
    transaction: ProcessedTransaction,
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
    if not classified_transaction_is_exported(
        config=config,
        labelled_receipts=labelled_receipts,
        processed_transaction=transaction,
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
            config=config,
            labelled_receipts=labelled_receipts,
            processed_transaction=transaction,
            csv_output_filepath=filepath,
            csv_encoding=csv_encoding,
        ):
            csv_asset_transactions: List[ProcessedTransaction] = (
                read_csv_to_asset_transactions(
                    labelled_receipts=labelled_receipts,
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
