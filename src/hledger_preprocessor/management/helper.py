import os
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
from typeguard import typechecked

from hledger_preprocessor.config.Config import Config
from hledger_preprocessor.config.load_config import (
    raw_receipt_img_filepath_to_cropped,
)
from hledger_preprocessor.csv_parsing.csv_to_transactions import (
    csv_to_transactions,
    load_csv_transactions_from_file_per_year,
)
from hledger_preprocessor.csv_parsing.preprocess_csvs import pre_process_csvs
from hledger_preprocessor.Currency import (
    Currency,
)
from hledger_preprocessor.dir_reading_and_writing import (
    assert_dir_full_hierarchy_exists,
)
from hledger_preprocessor.editing.edit_receipt_tui import tui_select_receipt
from hledger_preprocessor.generics.enums import ClassifierType, LogicType
from hledger_preprocessor.generics.Transaction import Transaction
from hledger_preprocessor.management.get_all_hledger_flow_accounts import (
    get_all_accounts,
)
from hledger_preprocessor.matching.linking.helper import (
    store_updated_receipt_label,
)
from hledger_preprocessor.reading_history.load_receipts_from_dir import (
    load_receipts_from_dir,
)
from hledger_preprocessor.receipts_to_objects.make_receipt_labels import (
    make_receipt_label,
)
from hledger_preprocessor.TransactionObjects.Receipt import Receipt

# Action 0.


@typechecked
def concatenate_asset_csvs(*, config: Config) -> None:
    asset_path: Path = Path(config.get_asset_path(assert_exists=False))

    # Ensure the output assets directory exists

    asset_path.mkdir(exist_ok=True)

    # Get all year directories (assuming they are named as years, e.g., "2023")
    year_dirs = [
        d for d in asset_path.iterdir() if d.is_dir() and d.name.isdigit()
    ]

    # Process each currency
    for currency in Currency:
        currency_files = []
        # Look for files in each year directory
        for year_dir in year_dirs:
            file_path = year_dir / f"Currency.{currency.value}.csv"
            if file_path.exists():
                currency_files.append(file_path)

        if currency_files:
            # Concatenate all CSV files for this currency
            dfs = [pd.read_csv(file) for file in currency_files]
            combined_df = pd.concat(dfs, ignore_index=True)

            # Save to output file
            output_file = asset_path / f"Currency.{currency.value}.csv"
            combined_df.to_csv(output_file, index=False)


@typechecked
def edit_receipt(*, config: Config, labelled_receipts: List[Receipt]) -> None:

    # List receipts that can be found.
    labelled_receipts: List[Receipt] = load_receipts_from_dir(config=config)

    # Show TUI that lists the receipt date, total amounts and raw_img_filepath and let user go through the list.
    selected_receipt: Receipt = tui_select_receipt(receipts=labelled_receipts)

    # If user presses enter, that receipt is loaded by calling:
    cropped_receipt_img_filepath: str = raw_receipt_img_filepath_to_cropped(
        config=config,
        raw_receipt_img_filepath=selected_receipt.raw_img_filepath,
    )

    modified_receipt: Receipt = make_receipt_label(
        config=config,
        raw_receipt_img_filepath=selected_receipt.raw_img_filepath,
        cropped_receipt_img_filepath=cropped_receipt_img_filepath,
        hledger_account_infos=get_all_accounts(
            config=config,
            labelled_receipts=labelled_receipts,
        ),
        receipt_nr=0,
        total_nr_of_receipts=1,
        labelled_receipts=[],
        prefilled_receipt=selected_receipt,
    )

    # If the modified receipt is not equal to the loaded receipt, export it.
    store_updated_receipt_label(latest_receipt=modified_receipt, config=config)


@typechecked
def preprocess_asset_csvs(
    *,
    config: Config,
    labelled_receipts: List[Receipt],
    models: Dict[ClassifierType, Dict[LogicType, Any]],
) -> None:

    # account_configs.extend(config.accounts)
    for asset_account_config in config.get_account_configs_without_csv():
        # for asset_account_config in config.asset_accounts:
        transactions_per_year_per_account: Dict[int, List[Transaction]] = (
            load_csv_transactions_from_file_per_year(
                config=config,
                labelled_receipts=labelled_receipts,
                abs_csv_filepath=asset_account_config.get_abs_csv_filepath(
                    dir_paths_config=config.dir_paths
                ),
                account_config=asset_account_config,
                csv_encoding=config.csv_encoding,
            )
        )

        # TODO: Throw warning or error if createRules is not included.
        # TODO: ensure the import directory is created.
        # TODO: re-enable
        # assert_dir_full_hierarchy_exists(
        #     account=account_config.account, working_subdir=config.get_working_subdir_path(assert_exists=False)
        # )
        pre_process_csvs(
            config=config,
            labelled_receipts=labelled_receipts,
            account_config=asset_account_config,
            transactions_per_year=transactions_per_year_per_account,
            ai_models_tnx_classification=models[
                ClassifierType.TRANSACTION_CATEGORY
            ][LogicType.AI],
            rule_based_models_tnx_classification=models[
                ClassifierType.TRANSACTION_CATEGORY
            ][LogicType.RULE_BASED],
        )
        assert_dir_full_hierarchy_exists(
            config=config,
            account=asset_account_config.account,
            working_subdir=config.get_working_subdir_path(assert_exists=False),
        )


def preprocess_generic_csvs(
    *,
    config: Config,
    labelled_receipts: List[Receipt],
    models: Dict[ClassifierType, Dict[LogicType, Any]],
) -> None:
    transactions_per_year_per_account: Dict[int, List[Transaction]] = {}

    for account_config in config.accounts:

        abs_csv_filepath: str = account_config.get_abs_csv_filepath(
            dir_paths_config=config.dir_paths
        )

        if os.path.isfile(path=abs_csv_filepath):

            transactions_per_year_per_account: Dict[int, List[Transaction]] = (
                csv_to_transactions(
                    config=config,
                    labelled_receipts=labelled_receipts,
                    input_csv_filepath=abs_csv_filepath,
                    csv_encoding=config.csv_encoding,
                    account_config=account_config,
                )
            )

            # TODO: Throw warning or error if createRules is not included.
            # TODO: ensure the import directory is created.
            # TODO: re-enable
            # assert_dir_full_hierarchy_exists(
            #     account=account_config.account, working_subdir=config.get_working_subdir_path(assert_exists=False)
            # )
            pre_process_csvs(
                config=config,
                labelled_receipts=labelled_receipts,
                account_config=account_config,
                transactions_per_year=transactions_per_year_per_account,
                ai_models_tnx_classification=models[
                    ClassifierType.TRANSACTION_CATEGORY
                ][LogicType.AI],
                rule_based_models_tnx_classification=models[
                    ClassifierType.TRANSACTION_CATEGORY
                ][LogicType.RULE_BASED],
            )
            assert_dir_full_hierarchy_exists(
                config=config,
                account=account_config.account,
                working_subdir=config.get_working_subdir_path(
                    assert_exists=False
                ),
            )
        else:
            print(f"SKIPPING FOR:{abs_csv_filepath}")
