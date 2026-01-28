import os
import shutil
from typing import Any, Dict, List

from typeguard import typechecked

from hledger_preprocessor.categorisation.categoriser import classify_transaction
from hledger_preprocessor.config.AccountConfig import AccountConfig
from hledger_preprocessor.config.Config import Config
from hledger_preprocessor.create_start import (
    export_csv_transactions_per_acount_into_each_year,
)
from hledger_preprocessor.csv_outputting.output_non_input_csv_transactions import (
    output_non_input_csv_transactions,
)
from hledger_preprocessor.csv_parsing.csv_to_transactions import (
    load_csv_transactions_from_file_per_year,
)
from hledger_preprocessor.dir_reading_and_writing import (
    assert_dir_full_hierarchy_exists,
)
from hledger_preprocessor.file_reading_and_writing import assert_file_exists
from hledger_preprocessor.generics.enums import ClassifierType, LogicType
from hledger_preprocessor.generics.Transaction import Transaction
from hledger_preprocessor.helper import assert_dir_exists, get_images_in_folder
from hledger_preprocessor.management.helper import (
    preprocess_asset_csvs,
    preprocess_generic_csvs,
)
from hledger_preprocessor.matching.helper import (
    prepare_transactions_per_account,
)
from hledger_preprocessor.matching.searching.matching import (
    manage_matching_receipts_to_transactions,
)
from hledger_preprocessor.receipt_transaction_matching.compare_transaction_to_receipt import (
    collect_non_csv_transactions,
)
from hledger_preprocessor.receipts_to_objects.edit_images.crop_image import (
    crop_images,
)
from hledger_preprocessor.receipts_to_objects.edit_images.rotate_all_images import (
    rotate_images,
)
from hledger_preprocessor.receipts_to_objects.make_receipt_labels import (
    manually_make_receipt_labels,
)
from hledger_preprocessor.rules.generate_rules_content import (
    generate_rules_file,
)
from hledger_preprocessor.TransactionObjects.AccountTransaction import (
    AccountTransaction,
)
from hledger_preprocessor.TransactionObjects.ProcessedTransaction import (
    ProcessedTransaction,
)
from hledger_preprocessor.TransactionObjects.Receipt import Receipt


# Action 0.
@typechecked
def manage_creating_new_setup(
    *, config: Config, labelled_receipts: List[Receipt]
) -> None:
    print("\n\nSTARTING NEW SETUP")

    for account_config in config.accounts:
        abs_csv_filepath: str = account_config.get_abs_csv_filepath(
            dir_paths_config=config.dir_paths
        )

        if os.path.isfile(abs_csv_filepath):
            transactions_per_year_per_account: Dict[int, List[Transaction]] = (
                load_csv_transactions_from_file_per_year(
                    config=config,
                    labelled_receipts=labelled_receipts,
                    abs_csv_filepath=abs_csv_filepath,
                    account_config=account_config,
                    csv_encoding=config.csv_encoding,
                )
            )

            export_csv_transactions_per_acount_into_each_year(
                config=config,
                account_config=account_config,
                transaction_years=list(
                    transactions_per_year_per_account.keys()
                ),
            )


# Action 1.
@typechecked
def manage_preprocessing_csvs(
    *,
    config: Config,
    models: Dict[ClassifierType, Dict[LogicType, Any]],
    labelled_receipts: List[Receipt],
) -> None:
    if (
        config.dir_paths.get_path("pre_processed_output_dir", absolute=True)
        is None
    ):
        raise ValueError(
            "config.dir_paths.get_path('pre_processed_output_dir',"
            " absolute=True ) should be set with args.pre_processed_output_dir"
        )

    preprocess_asset_csvs(
        config=config, labelled_receipts=labelled_receipts, models=models
    )

    preprocess_generic_csvs(
        config=config, labelled_receipts=labelled_receipts, models=models
    )


@typechecked
def manage_preprocessing_assets(
    *,
    config: Config,
    models: Dict[ClassifierType, Dict[LogicType, Any]],
    labelled_receipts: List[Receipt],
) -> None:
    # found_asset_years: List[int] = [2023, 2024, 2025]  # TODO: get from code.

    # Remove asset directory:
    asset_path: str = config.dir_paths.get_path(
        path_name="asset_transaction_csvs_dir", absolute=True
    )

    if os.path.isdir(asset_path):
        shutil.rmtree(asset_path)

    assert not os.path.exists(asset_path)

    non_input_csv_transactions: Dict[
        AccountConfig, List[ProcessedTransaction]
    ] = {}
    for account_config in config.get_account_configs_without_csv():
        non_input_csv_transactions[account_config] = []

    # relevant_transactions:Dict[Receipt,List[Transaction]]={}
    for labelled_receipt in labelled_receipts:
        # for net_bought_item in labelled_receipt.net_bought_items:
        all_account_transactions: List[AccountTransaction] = (
            collect_non_csv_transactions(receipt=labelled_receipt)
        )

        for receipt_account_transaction in all_account_transactions:

            for account_config in config.get_account_configs_without_csv():
                if (
                    receipt_account_transaction.account
                    == account_config.account
                ):
                    receipt_account_transaction.set_parent_receipt_category(
                        parent_receipt_category=labelled_receipt.receipt_category
                    )

                    classified_txn: ProcessedTransaction = classify_transaction(
                        txn=receipt_account_transaction,
                        ai_models_tnx_classification=models[
                            ClassifierType.TRANSACTION_CATEGORY
                        ][LogicType.AI],
                        rule_based_models_tnx_classification=models[
                            ClassifierType.TRANSACTION_CATEGORY
                        ][LogicType.RULE_BASED],
                        category_namespace=config.category_namespace,
                        parent_receipt=labelled_receipt,
                    )

                    non_input_csv_transactions[account_config].append(
                        classified_txn
                        # ProcessedTransaction(
                        #     transaction=receipt_account_transaction,
                        #     parent_receipt=labelled_receipt,
                        # )
                    )

            # TODO: loop over receipt labels and get the transactions from that account respectively.

    output_non_input_csv_transactions(
        labelled_receipts=labelled_receipts,
        config=config,
        non_input_csv_transactions=non_input_csv_transactions,
    )


# Action 2
@typechecked
def manage_generating_rules(*, config: Config) -> None:

    for account_config in config.accounts:
        assert_dir_full_hierarchy_exists(
            config=config,
            account=account_config.account,
            working_subdir=config.get_working_subdir_path(assert_exists=False),
        )
        generate_rules_file(
            config=config,
            account_config=account_config,
        )


@typechecked
def manage_creating_receipt_img_labels_with_tui(
    *, config: Config, labelled_receipts: List[Receipt], verbose: bool
) -> Dict[str, Receipt]:
    # Ensure directories exist
    assert_dir_exists(
        dirpath=config.dir_paths.get_path(
            "receipt_images_input_dir", absolute=True
        )
    )
    assert_dir_exists(
        dirpath=config.dir_paths.get_path("receipt_labels_dir", absolute=True)
    )
    os.makedirs(
        config.dir_paths.get_path("receipt_images_input_dir", absolute=True),
        exist_ok=True,
    )
    os.makedirs(
        config.dir_paths.get_path(
            "receipt_images_processed_dir", absolute=True
        ),
        exist_ok=True,
    )

    filepath_receipt_object: Dict[str, Receipt] = {}

    raw_receipt_img_filepaths: List[str] = get_images_in_folder(
        folder_path=config.dir_paths.get_path(
            "receipt_images_input_dir", absolute=True
        )
    )

    # Step 1: Rotate all images
    rotate_images(
        raw_receipt_img_filepaths=raw_receipt_img_filepaths, config=config
    )

    # Step 2: Crop all images
    crop_images(
        raw_receipt_img_filepaths=raw_receipt_img_filepaths, config=config
    )

    receipt_per_raw_img_filepath: Dict[str, Receipt] = (
        manually_make_receipt_labels(
            config=config,
            raw_receipt_img_filepaths=raw_receipt_img_filepaths,
            labelled_receipts=labelled_receipts,
            verbose=verbose,
        )
    )

    # Assert receipts exist
    for (
        raw_receipt_img_filepath,
        receipt_obj,
    ) in receipt_per_raw_img_filepath.items():
        assert_file_exists(filepath=raw_receipt_img_filepath)
        if raw_receipt_img_filepath in filepath_receipt_object:
            raise ValueError(
                "Error, overwriting a receipt at"
                f" filepath:{raw_receipt_img_filepath}, it is already"
                " processed."
            )
        filepath_receipt_object[raw_receipt_img_filepath] = receipt_obj

    return filepath_receipt_object


@typechecked
def manage_getting_manual_receipt_labels(
    *,
    config: Config,
    only_get_existing_jsons: bool,
    labelled_receipts: List[Receipt],
) -> Dict[str, Receipt]:
    if only_get_existing_jsons:
        # TODO: don't ask the user to make additional labels, just work with the ones you have.
        raise NotImplementedError(
            "Did not write load receipts from file without additional tui call."
        )
    else:
        # return manage_creating_receipt_img_labels_with_tui(
        #     args=args, csv_encoding=csv_encoding
        # )
        return manage_creating_receipt_img_labels_with_tui(
            config=config,
            verbose=False,
            labelled_receipts=labelled_receipts,
        )


@typechecked
def manage_matching_manual_receipt_objs_to_account_transactions(
    *,
    config: Config,
    models: Dict[ClassifierType, Dict[LogicType, Any]],
    labelled_receipts: List[Receipt],
) -> None:
    json_paths_receipt_objs: Dict[str, Receipt] = (
        manage_getting_manual_receipt_labels(
            config=config,
            labelled_receipts=labelled_receipts,
            only_get_existing_jsons=False,
        )
    )

    manage_matching_receipts_to_transactions(
        config=config,
        labelled_receipts=labelled_receipts,
        json_paths_receipt_objs=json_paths_receipt_objs,
        csv_transactions_per_account=prepare_transactions_per_account(
            labelled_receipts=labelled_receipts,
            config=config,
        ),
        models=models,
    )
