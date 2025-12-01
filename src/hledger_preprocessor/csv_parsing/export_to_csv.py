import csv
import os
from pathlib import Path
from typing import List

from typeguard import typechecked

from hledger_preprocessor.config.AccountConfig import AccountConfig
from hledger_preprocessor.csv_parsing.check_assets_in_csv_status import (
    classified_transaction_is_exported,
)
from hledger_preprocessor.generics.Transaction import Transaction
from hledger_preprocessor.TransactionTypes.AssetTransaction import (
    AssetTransaction,
)


@typechecked
def write_processed_csv(
    transactions: List[Transaction],
    account_config: AccountConfig,
    filepath: str,
) -> None:
    # Get fieldnames dynamically from the first object in the list
    if transactions:
        fieldnames = list(
            transactions[0].to_hledger_dict().keys()
        )  # Convert to list
        # Prepend fields if not already present
        if "account_holder" not in fieldnames:
            # Order: transaction_code, account_holder, bank, account_type
            fieldnames.insert(0, "account_type")
            fieldnames.insert(0, "bank")
            fieldnames.insert(0, "account_holder")
            fieldnames.insert(0, "base_currency")

        if "amount0" in fieldnames:
            fieldnames[fieldnames.index("amount0")] = "amount"
        # if "transaction_code" not in fieldnames:
        #     if fieldnames["amount"] > 0:
        #         fieldnames["transaction_code"] = TransactionCode.DEBIT.value
        #     else:
        #         fieldnames["transaction_code"] = TransactionCode.CREDIT.value
        if "nr_in_batch" not in fieldnames:
            fieldnames.insert(0, "nr_in_batch")
        with open(filepath, mode="w", encoding="utf-8", newline="") as outfile:
            writer = csv.DictWriter(
                outfile, fieldnames=fieldnames, quoting=csv.QUOTE_ALL
            )
            writer.writeheader()

            # Write each transaction as a row in the CSV
            for i, txn in enumerate(transactions):
                some_dict = txn.to_hledger_dict()
                # Remove unwanted keys
                if "other_party" in some_dict:
                    some_dict.pop("other_party")  # TODO: re-enable
                if "asset_account" in some_dict:
                    some_dict.pop("asset_account")  # TODO: re-enable

                # Prepend fields to dictionary
                if "nr_in_batch" not in some_dict.keys():
                    new_dict = {
                        "nr_in_batch": i,
                        "account_holder": account_config.account.account_holder,
                        "bank": account_config.account.bank,
                        "account_type": account_config.account.account_type,
                    }
                else:
                    new_dict = {
                        "account_holder": account_config.account.account_holder,
                        "bank": account_config.account.bank,
                        "account_type": account_config.account.account_type,
                    }
                new_dict.update(some_dict)  # Append remaining key-value pairs
                some_dict = new_dict

                writer.writerow(some_dict)


@typechecked
def write_asset_transaction_to_csv(
    transaction: AssetTransaction,  # Changed to single AssetTransaction
    filepath: str,
    csv_encoding: str = "utf-8",  # Added encoding parameter for consistency
) -> None:
    """
    Export a single AssetTransaction to a CSV file.
    - Checks if the transaction is already in the file (raises ValueError if it is).
    - Appends the transaction if it is not present.
    - Asserts that the transaction was successfully added.

    Args:
        transaction: The AssetTransaction to export.
        filepath: The path to the CSV file.
        csv_encoding: The encoding to use for reading/writing the CSV file (default: utf-8).

    Raises:
        ValueError: If the transaction is already in the CSV file.
    """
    # Define fieldnames explicitly to preserve order
    fieldnames = [
        "date",
        "account_holder",
        "bank",
        "account_type",
        "currency",
        "amount",
        "transaction_code",
        "other_party",
        "asset_account",
        "parent_receipt_category",
        "raw_receipt_img_filepath",
        "ai_classification",
        "logic_classification",
    ]

    # Convert transaction to dictionary for comparison and writing
    txn_dict = transaction.to_hledger_dict()

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
                outfile, fieldnames=fieldnames, quoting=csv.QUOTE_ALL
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
            raise AssertionError(
                f"Failed to verify transaction in \n{filepath}:"
                f" with:\n{txn_dict}"
            )

    else:
        raise ValueError(
            f"Transaction already exists in {filepath}: {txn_dict}"
        )
