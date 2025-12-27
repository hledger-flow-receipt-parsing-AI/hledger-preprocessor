from dataclasses import MISSING, fields
from decimal import Decimal
from typing import Any, List

from typeguard import typechecked

from hledger_preprocessor.categorisation.Categories import CategoryNamespace
from hledger_preprocessor.categorisation.categoriser import classify_transaction
from hledger_preprocessor.config.helper import get_input_csv, has_input_csv
from hledger_preprocessor.config.load_config import Config
from hledger_preprocessor.csv_parsing.read_csv_asset_transactions import (
    read_csv_to_asset_transactions,
)
from hledger_preprocessor.generics.Transaction import Transaction
from hledger_preprocessor.TransactionObjects.Account import Account
from hledger_preprocessor.TransactionObjects.AccountTransaction import (
    AccountTransaction,
)
from hledger_preprocessor.TransactionObjects.ProcessedTransaction import (
    ProcessedTransaction,
)
from hledger_preprocessor.TransactionObjects.Receipt import Receipt


@typechecked
def _transaction_key(*, tnx: "AccountTransaction") -> tuple[Any, ...]:
    """
    Automatically return a tuple of only the REQUIRED fields
    (those without default or default_factory) of the dataclass.

    This ensures we compare only meaningful business keys,
    ignoring optional/auto-generated fields like id, exported, etc.

    Raises AttributeError if trying to access a non-existent field.
    """
    required_fields = [
        f
        for f in fields(tnx)
        if f.default is MISSING and f.default_factory is MISSING
    ]
    # print(f'required_fields={required_fields}')
    # Extract values safely — will raise AttributeError if field missing (shouldn't happen)
    return tuple(getattr(tnx, f.name) for f in required_fields)


@typechecked
def classified_transaction_is_exported(
    *,
    config: Config,
    labelled_receipts: List[Receipt],
    processed_transaction: ProcessedTransaction,
    csv_output_filepath: str,
    csv_encoding: str,
) -> bool:
    """
    Returns True if a transaction with the same business key already exists in the CSV.
    Igbles optional/auto-generated fields like id, exported flag, etc.
    """
    csv_asset_transactions: List[ProcessedTransaction] = (
        read_csv_to_asset_transactions(
            labelled_receipts=labelled_receipts,
            csv_filepath=csv_output_filepath,
            csv_encoding=csv_encoding,
        )
    )

    my_key = _transaction_key(tnx=processed_transaction.transaction)

    for i, tnx in enumerate(csv_asset_transactions):
        if _transaction_key(tnx=tnx.transaction) == my_key:
            if (
                tnx.parent_receipt.raw_img_filepath
                == processed_transaction.parent_receipt.raw_img_filepath
            ):
                return True

    return False


@typechecked
def unclassified_transaction_can_be_exported(
    *,
    config: Config,
    account: Account,
):
    return has_input_csv(config=config, account=account)


@typechecked
def unclassified_transaction_is_exported(
    *,
    config: Config,
    search_receipt_account_transaction: AccountTransaction,
    parent_receipt: Receipt,
    csv_encoding: str = "utf-8",
    ai_models_tnx_classification: List,
    rule_based_models_tnx_classification: List,
    category_namespace: CategoryNamespace,
) -> bool:

    csv_output_filepath: str = get_input_csv(
        config=config, account=search_receipt_account_transaction.account
    )

    classified_transaction: Transaction = get_classified_transaction(
        search_receipt_account_transaction=search_receipt_account_transaction,
        parent_receipt=parent_receipt,
        ai_models_tnx_classification=ai_models_tnx_classification,
        rule_based_models_tnx_classification=rule_based_models_tnx_classification,
        category_namespace=category_namespace,
    )

    return classified_transaction_is_exported(
        asset_transaction=classified_transaction,
        csv_output_filepath=csv_output_filepath,
        csv_encoding=csv_encoding,
    )


@typechecked
def get_classified_transaction(
    *,
    search_receipt_account_transaction: AccountTransaction,
    parent_receipt: Receipt,
    ai_models_tnx_classification: List,
    rule_based_models_tnx_classification: List,
    category_namespace: CategoryNamespace,
) -> ProcessedTransaction:

    amount_paid = Decimal(str(search_receipt_account_transaction.amount_paid))
    change_returned = Decimal(
        str(search_receipt_account_transaction.change_returned)
    )
    amount0 = amount_paid - change_returned  # Prevent rounding error in float.

    classified_transaction: ProcessedTransaction = classify_transaction(
        txn=search_receipt_account_transaction,
        ai_models_tnx_classification=ai_models_tnx_classification,
        rule_based_models_tnx_classification=rule_based_models_tnx_classification,
        category_namespace=category_namespace,
    )
    return classified_transaction
