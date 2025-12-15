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
from hledger_preprocessor.TransactionObjects.Receipt import Receipt


def _transaction_key(tnx: "AccountTransaction") -> tuple[Any, ...]:
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

    # Extract values safely — will raise AttributeError if field missing (shouldn't happen)
    return tuple(getattr(tnx, f.name) for f in required_fields)


# def _transaction_key(tnx: "AccountTransaction") -> tuple:
#     """
#     Return a tuple of only the fields that define transactional identity.
#     Adjust this list to match what makes two transactions "the same" in your domain.
#     """

#     # Exclude fields that are optional or have default values)
#     return tuple(
#         getattr(tnx, f.name)
#         for f in fields(tnx)
#         if f.default is f.default_factory
#         and f.default is None  # rough heuristic for "required"
#         or f.name
#         in {
#             "the_date",
#             "amount",
#             "currency",
#             "description",
#             "account",
#         }  # force include
#     )


def classified_transaction_is_exported(
    *,
    asset_transaction: "AccountTransaction",
    csv_output_filepath: str,
    csv_encoding: str,
) -> bool:
    """
    Returns True if a transaction with the same business key already exists in the CSV.
    Igbles optional/auto-generated fields like id, exported flag, etc.
    """
    csv_asset_transactions: List["AccountTransaction"] = (
        read_csv_to_asset_transactions(
            csv_filepath=csv_output_filepath,
            csv_encoding=csv_encoding,
        )
    )

    my_key = _transaction_key(asset_transaction)

    for tnx in csv_asset_transactions:
        if _transaction_key(tnx) == my_key:
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
    # Generate output path
    # asset_path: str = ensure_asset_path_is_created(config=config)
    # csv_output_filepath: str = get_asset_csv_output_path(
    #     asset_path=asset_path,
    #     account=search_receipt_account_transaction.account,
    #     year=parent_receipt.the_date.year,
    #     csv_filename=f"{search_receipt_account_transaction.currency}.csv",
    # )
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
) -> Transaction:

    amount_paid = Decimal(str(search_receipt_account_transaction.amount_paid))
    change_returned = Decimal(
        str(search_receipt_account_transaction.change_returned)
    )
    amount0 = amount_paid - change_returned  # Prevent rounding error in float.

    classified_transaction: Transaction = classify_transaction(
        txn=search_receipt_account_transaction,
        ai_models_tnx_classification=ai_models_tnx_classification,
        rule_based_models_tnx_classification=rule_based_models_tnx_classification,
        category_namespace=category_namespace,
    )
    return classified_transaction
