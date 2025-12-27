from pprint import pprint
from typing import List

from typeguard import typechecked

from hledger_preprocessor.config.AccountConfig import AccountConfig
from hledger_preprocessor.config.helper import get_account_config, has_input_csv
from hledger_preprocessor.config.load_config import Config
from hledger_preprocessor.csv_parsing.check_assets_in_csv_status import (
    classified_transaction_is_exported,
    get_classified_transaction,
)
from hledger_preprocessor.csv_parsing.export_to_csv import (  # export_asset_transactions_to_csv,
    write_asset_transaction_to_csv,
)
from hledger_preprocessor.csv_parsing.read_csv_asset_transactions import (
    read_csv_to_asset_transactions,
)
from hledger_preprocessor.dir_reading_and_writing import (
    ensure_asset_path_is_created,
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
def export_asset_transaction_to_csv(
    *,
    config: Config,
    labelled_receipts: List[Receipt],
    search_receipt_account_transaction: AccountTransaction,
    parent_receipt: Receipt,
    csv_encoding: str = "utf-8",
    ai_models_tnx_classification: List,
    rule_based_models_tnx_classification: List,
) -> None:
    """
    Export an asset transaction to a CSV file, organized by year.
    Avoids appending duplicate transactions.
    """
    # if search_receipt_account_transaction.account.asset_type != AssetType.ASSET:
    #     raise ValueError(
    #         "Expected found asset transaction to be of type asset."
    #     )
    # TODO: assert it has not yet been outputted.
    if not has_input_csv(
        config=config,
        account=search_receipt_account_transaction.account,
    ):

        asset_path: str = ensure_asset_path_is_created(config=config)
        account_config: AccountConfig = get_account_config(
            config=config, account=search_receipt_account_transaction.account
        )
        # Generate output path
        # csv_output_filepath: str = get_asset_csv_output_path(
        #     asset_path=asset_path,
        #     account=search_receipt_account_transaction.account,
        #     year=parent_receipt.the_date.year,
        #     csv_filename=f"{search_receipt_account_transaction.currency}.csv",
        # )
        csv_output_filepath: str = account_config.get_abs_csv_filepath(
            dir_paths_config=config.dir_paths
        )
        csv_asset_transactions: List[ProcessedTransaction] = (
            read_csv_to_asset_transactions(
                csv_filepath=csv_output_filepath,
                csv_encoding=csv_encoding,
                labelled_receipts=labelled_receipts,
            )
        )

        classified_transaction: Transaction = get_classified_transaction(
            search_receipt_account_transaction=search_receipt_account_transaction,
            parent_receipt=parent_receipt,
            ai_models_tnx_classification=ai_models_tnx_classification,
            rule_based_models_tnx_classification=rule_based_models_tnx_classification,
        )

        if classified_transaction not in csv_asset_transactions:
            csv_asset_transactions.append(classified_transaction)
        else:
            raise ValueError("The transaction is already exported.")

        # TODO: determine why all asset transactions are exported instead of only this one.
        write_asset_transaction_to_csv(
            config=config,
            transaction=classified_transaction,
            filepath=csv_output_filepath,
            account_config=account_config,
        )
        if not classified_transaction_is_exported(
            labelled_receipts=labelled_receipts,
            processed_transaction=classified_transaction,
            csv_output_filepath=csv_output_filepath,
            csv_encoding=csv_encoding,
        ):
            print_transactions(csv_asset_transactions=[classified_transaction])
            raise ValueError(
                "Should have exported the asset transaction by now."
            )
    else:
        raise ValueError("Should not reach this state.")


@typechecked
def print_transactions(
    *, csv_asset_transactions: List[AccountTransaction]
) -> None:
    for i, csv_asset_transaction in enumerate(csv_asset_transactions):
        print(f"{i}, hash={csv_asset_transaction.get_hash()}")
        pprint(csv_asset_transaction)
    if len(csv_asset_transactions) == 0:
        raise ValueError("No transaction found.")
