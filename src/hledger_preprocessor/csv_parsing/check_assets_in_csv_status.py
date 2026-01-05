from dataclasses import MISSING, fields
from typing import Any, List

from typeguard import typechecked

from hledger_preprocessor.categorisation.Categories import CategoryNamespace
from hledger_preprocessor.categorisation.categoriser import classify_transaction
from hledger_preprocessor.config.Config import Config
from hledger_preprocessor.config.helper import get_input_csv, has_input_csv
from hledger_preprocessor.csv_parsing.read_csv_asset_transactions import (
    read_csv_to_asset_transactions,
)
from hledger_preprocessor.matching.ask_user_action import ActionDataset
from hledger_preprocessor.TransactionObjects.Account import Account
from hledger_preprocessor.TransactionObjects.AccountTransaction import (
    AccountTransaction,
)
from hledger_preprocessor.TransactionObjects.ProcessedTransaction import (
    ProcessedTransaction,
)
from hledger_preprocessor.TransactionObjects.Receipt import Receipt


@typechecked
def unclassified_transaction_can_be_exported(
    *,
    config: Config,
    account: Account,
):
    return has_input_csv(config=config, account=account)


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
    # config: Config,
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
def unclassified_transaction_is_exported(
    *,
    action_dataset: ActionDataset,
    # config: Config,`
    # search_receipt_account_transaction: AccountTransaction,
    # parent_receipt: Receipt,
    csv_encoding: str = "utf-8",
    # ai_models_tnx_classification: List,
    # rule_based_models_tnx_classification: List,
    # category_namespace: CategoryNamespace,`
) -> bool:

    csv_output_filepath: str = get_input_csv(
        config=action_dataset.config,
        account=action_dataset.search_receipt_account_transaction.account,
    )

    classified_transaction: ProcessedTransaction = get_classified_transaction(
        search_receipt_account_transaction=action_dataset.search_receipt_account_transaction,
        parent_receipt=action_dataset.receipt,
        ai_models_tnx_classification=action_dataset.ai_models_tnx_classification,
        rule_based_models_tnx_classification=action_dataset.rule_based_models_tnx_classification,
        category_namespace=action_dataset.config.category_namespace,
    )

    return classified_transaction_is_exported(
        # config=action_dataset.config,
        labelled_receipts=action_dataset.labelled_receipts,
        processed_transaction=classified_transaction,
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

    # tendered_amount_out = Decimal(str(search_receipt_account_transaction.tendered_amount_out))
    # change_returned = Decimal(
    #     str(search_receipt_account_transaction.change_returned)
    # )
    # net_amount_out = tendered_amount_out - change_returned  # Prevent rounding error in float.
    if search_receipt_account_transaction.parent_receipt_category is None:
        search_receipt_account_transaction.set_parent_receipt_category(
            parent_receipt_category=parent_receipt.receipt_category
        )
    # TODO: remove or use it.
    classified_transaction: ProcessedTransaction = classify_transaction(
        parent_receipt=parent_receipt,
        txn=search_receipt_account_transaction,
        ai_models_tnx_classification=ai_models_tnx_classification,
        rule_based_models_tnx_classification=rule_based_models_tnx_classification,
        category_namespace=category_namespace,
    )
    return classified_transaction
