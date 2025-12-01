from decimal import Decimal
from typing import List

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
from hledger_preprocessor.TransactionTypes.AssetTransaction import (
    AssetTransaction,
)


def classified_transaction_is_exported(
    *,
    asset_transaction: AssetTransaction,
    csv_output_filepath: str,
    csv_encoding: str,
) -> bool:
    csv_asset_transactions: List[AssetTransaction] = (
        read_csv_to_asset_transactions(
            csv_filepath=csv_output_filepath,
            csv_encoding=csv_encoding,
        )
    )
    return asset_transaction in csv_asset_transactions


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
    asset_transaction: AssetTransaction = AssetTransaction(
        the_date=parent_receipt.the_date,
        currency=search_receipt_account_transaction.currency,
        amount0=float(amount0),
        other_party=parent_receipt.shop_identifier,
        asset_account=search_receipt_account_transaction.account,
        parent_receipt_category=parent_receipt.receipt_category,
        ai_classification=parent_receipt.ai_receipt_categorisation,
        logic_classification=parent_receipt.receipt_category,
        raw_receipt_img_filepath=parent_receipt.raw_img_filepath,
    )

    classified_transaction: Transaction = classify_transaction(
        txn=asset_transaction,
        ai_models_tnx_classification=ai_models_tnx_classification,
        rule_based_models_tnx_classification=rule_based_models_tnx_classification,
        category_namespace=category_namespace,
    )
    return classified_transaction
