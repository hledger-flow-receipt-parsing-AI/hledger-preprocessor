import os
from typing import Any, Dict, List, Optional, Tuple

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
def edit_receipt(*, config: Config, labelled_receipts: List[Receipt]) -> None:

    # List receipts that can be found.
    labelled_receipts: List[Receipt] = load_receipts_from_dir(config=config)

    # Show TUI that lists the receipt date, total amounts and raw_img_filepath and let user go through the list.  # noqa: E501
    selected_receipt: Receipt = tui_select_receipt(receipts=labelled_receipts)

    # If user presses enter, that receipt is loaded by calling:
    cropped_receipt_img_filepath: str = raw_receipt_img_filepath_to_cropped(
        config=config,
        raw_receipt_img_filepath=selected_receipt.raw_img_filepath,
    )

    hledger_account_infos, csv_transactions_per_account = get_all_accounts(
        config=config,
        labelled_receipts=labelled_receipts,
    )
    modified_receipt: Receipt = make_receipt_label(
        config=config,
        raw_receipt_img_filepaths=selected_receipt.raw_img_filepaths,
        cropped_receipt_img_filepath=cropped_receipt_img_filepath,
        hledger_account_infos=hledger_account_infos,
        csv_transactions_per_account=csv_transactions_per_account,
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
        #     account=account_config.account, working_subdir=config.get_working_subdir_path(assert_exists=False)  # noqa: E501
        # )
        pre_process_csvs(
            config=config,
            labelled_receipts=labelled_receipts,
            account_config=asset_account_config,
            transactions_per_year=transactions_per_year_per_account,
            ai_models_tnx_classification=models[
                ClassifierType.TRANSACTION_CATEGORY
            ].get(LogicType.AI, []),
            rule_based_models_tnx_classification=models[
                ClassifierType.TRANSACTION_CATEGORY
            ][LogicType.RULE_BASED],
        )
        assert_dir_full_hierarchy_exists(
            config=config,
            account=asset_account_config.account,
            working_subdir=config.get_working_subdir_path(assert_exists=False),
        )


def match_csv_to_csv(
    *,
    config: Config,
    labelled_receipts: List[Receipt],
) -> Tuple[Dict, Dict[str, str]]:
    """Reconcile linked-account CSV transactions.

    Parses all CSVs, runs the reconciliation matcher (auto-matching
    same-currency transfers, prompting for cross-currency ones), and
    returns:
      - suppress_ids: AccountConfig → set of transaction id() values
        to suppress during preprocessing.
      - category_overrides: txn_hash → linked account string for
        cross-currency CSV-to-CSV matches (both sides kept, but
        re-categorised to use equity:clearing).
    """
    from hledger_preprocessor.config.AccountConfig import AccountConfig as AC
    from hledger_preprocessor.generics.GenericTransactionWithCsv import (
        GenericCsvTransaction,
    )
    from hledger_preprocessor.reconciliation.reconcile_linked_accounts import (
        reconcile_linked_accounts,
    )

    suppress_ids: Dict[AC, set] = {}
    category_overrides: Dict[str, str] = {}

    has_linked = any(ac.linked_accounts for ac in config.accounts)
    if not has_linked:
        return suppress_ids, category_overrides

    # Parse all CSVs
    parsed: Dict[AC, Dict[int, List[Transaction]]] = {}
    for account_config in config.accounts:
        abs_csv_filepath = account_config.get_abs_csv_filepath(
            dir_paths_config=config.dir_paths
        )
        if os.path.isfile(path=abs_csv_filepath):
            parsed[account_config] = csv_to_transactions(
                config=config,
                labelled_receipts=labelled_receipts,
                input_csv_filepath=abs_csv_filepath,
                csv_encoding=config.csv_encoding,
                account_config=account_config,
            )

    # Flatten year-based dicts for reconciliation
    flat_txns: Dict[AC, List] = {}
    for ac, txns_by_year in parsed.items():
        flat = []
        for year_txns in txns_by_year.values():
            flat.extend(year_txns)
        flat_txns[ac] = flat

    generic_txns = {
        ac: [t for t in txns if isinstance(t, GenericCsvTransaction)]
        for ac, txns in flat_txns.items()
    }
    matches_path = os.path.join(
        config.dir_paths.root_finance_path,
        "csv_reconciliation_matches.json",
    )
    suppressed, category_overrides = reconcile_linked_accounts(
        transactions_per_account=generic_txns,
        matches_path=matches_path,
    )

    for ac, indices in suppressed.items():
        suppress_ids[ac] = {id(generic_txns[ac][i]) for i in indices}

    return suppress_ids, category_overrides


def preprocess_generic_csvs(
    *,
    config: Config,
    labelled_receipts: List[Receipt],
    models: Dict[ClassifierType, Dict[LogicType, Any]],
    suppress_ids: Optional[Dict] = None,
    category_overrides: Optional[Dict[str, str]] = None,
) -> None:
    from hledger_preprocessor.config.AccountConfig import AccountConfig as AC
    from hledger_preprocessor.generics.GenericTransactionWithCsv import (
        GenericCsvTransaction,
    )
    from hledger_preprocessor.reconciliation.reconcile_linked_accounts import (
        reconcile_linked_accounts,
    )

    has_linked = any(ac.linked_accounts for ac in config.accounts)

    if has_linked:
        # Parse all CSVs once
        parsed: Dict[AC, Dict[int, List[Transaction]]] = {}
        for account_config in config.accounts:
            abs_csv_filepath = account_config.get_abs_csv_filepath(
                dir_paths_config=config.dir_paths
            )
            if os.path.isfile(path=abs_csv_filepath):
                parsed[account_config] = csv_to_transactions(
                    config=config,
                    labelled_receipts=labelled_receipts,
                    input_csv_filepath=abs_csv_filepath,
                    csv_encoding=config.csv_encoding,
                    account_config=account_config,
                )

        if suppress_ids is None:
            # Run reconciliation on the SAME parsed transactions
            flat_generic: Dict[AC, List] = {}
            for ac, txns_by_year in parsed.items():
                flat = []
                for year_txns in txns_by_year.values():
                    flat.extend(year_txns)
                flat_generic[ac] = [
                    t for t in flat if isinstance(t, GenericCsvTransaction)
                ]

            matches_path = os.path.join(
                config.dir_paths.root_finance_path,
                "csv_reconciliation_matches.json",
            )
            suppressed_indices, category_overrides = reconcile_linked_accounts(
                transactions_per_account=flat_generic,
                matches_path=matches_path,
            )

            # Convert index-based suppression to id()-based on the
            # SAME transaction objects that will be processed below.
            suppress_ids = {}
            for ac, indices in suppressed_indices.items():
                suppress_ids[ac] = {id(flat_generic[ac][i]) for i in indices}

        # Filter suppressed transactions from year-based dicts
        if suppress_ids:
            for ac, txns_by_year in parsed.items():
                if suppress_ids.get(ac):
                    for year, txns in txns_by_year.items():
                        txns_by_year[year] = [
                            t for t in txns if id(t) not in suppress_ids[ac]
                        ]

        # Process
        for account_config, transactions_per_year_per_account in parsed.items():
            pre_process_csvs(
                config=config,
                labelled_receipts=labelled_receipts,
                account_config=account_config,
                transactions_per_year=transactions_per_year_per_account,
                ai_models_tnx_classification=models[
                    ClassifierType.TRANSACTION_CATEGORY
                ].get(LogicType.AI, []),
                rule_based_models_tnx_classification=models[
                    ClassifierType.TRANSACTION_CATEGORY
                ][LogicType.RULE_BASED],
                category_overrides=category_overrides,
            )
            assert_dir_full_hierarchy_exists(
                config=config,
                account=account_config.account,
                working_subdir=config.get_working_subdir_path(
                    assert_exists=False
                ),
            )
    else:
        # Original single-pass approach (no linked accounts)
        for account_config in config.accounts:
            abs_csv_filepath = account_config.get_abs_csv_filepath(
                dir_paths_config=config.dir_paths
            )
            if os.path.isfile(path=abs_csv_filepath):
                transactions_per_year_per_account = csv_to_transactions(
                    config=config,
                    labelled_receipts=labelled_receipts,
                    input_csv_filepath=abs_csv_filepath,
                    csv_encoding=config.csv_encoding,
                    account_config=account_config,
                )
                pre_process_csvs(
                    config=config,
                    labelled_receipts=labelled_receipts,
                    account_config=account_config,
                    transactions_per_year=transactions_per_year_per_account,
                    ai_models_tnx_classification=models[
                        ClassifierType.TRANSACTION_CATEGORY
                    ].get(LogicType.AI, []),
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
