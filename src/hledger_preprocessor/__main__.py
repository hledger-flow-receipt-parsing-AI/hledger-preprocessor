"""Entry point for the project."""

import os
import sys
import warnings

# Suppress TensorFlow/CUDA/absl warnings before any imports
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"
os.environ["ABSL_MIN_LOG_LEVEL"] = "3"
os.environ["GRPC_VERBOSITY"] = "ERROR"
os.environ["GLOG_minloglevel"] = "2"
warnings.filterwarnings("ignore", category=UserWarning, module="transformers")
warnings.filterwarnings("ignore", category=FutureWarning, module="transformers")
warnings.filterwarnings("ignore", category=RuntimeWarning, module="runpy")

from argparse import Namespace
from typing import Any, Dict, List

from typeguard import typechecked

from hledger_preprocessor.arg_parser import (
    assert_args_are_valid,
    create_arg_parser,
)
from hledger_preprocessor.checks.check_categorisation import (
    check_categorisation,
)
from hledger_preprocessor.checks.check_matching import check_matching
from hledger_preprocessor.config.load_config import Config, load_config
from hledger_preprocessor.generics.enums import ClassifierType, LogicType
from hledger_preprocessor.get_models import get_models
from hledger_preprocessor.management.helper import edit_receipt
from hledger_preprocessor.management.main_manager import (
    manage_batch_match_receipts,
    manage_creating_new_setup,
    manage_creating_receipt_img_labels_with_tui,
    manage_generating_rules,
    manage_match_csv_to_csv,
    manage_matching_manual_receipt_objs_to_account_transactions,
    manage_preprocessing_assets,
    manage_preprocessing_csvs,
)
from hledger_preprocessor.reading_history.load_receipts_from_dir import (
    load_receipts_from_dir,
)
from hledger_preprocessor.TransactionObjects.Receipt import Receipt


@typechecked
def main() -> None:
    # Parse input arguments
    parser = create_arg_parser()

    ## NEW
    args: Namespace = parser.parse_args()
    assert_args_are_valid(args=args)

    # --map-csv runs before anything else: it only needs the config path,
    # not a fully loaded Config (the CSV may not be in config yet).
    if args.map_csv:
        from hledger_preprocessor.csv_mapping.mapping_tui import (
            run_csv_mapping_tui,
        )

        run_csv_mapping_tui(
            csv_filepath=args.map_csv,
            config_path=args.config,
        )
        return  # mapping done — exit

    config: Config = load_config(
        config_path=args.config,
        pre_processed_output_dir=args.pre_processed_output_dir,
    )

    labelled_receipts: List[Receipt] = load_receipts_from_dir(config=config)

    # --- Pre-flight checks (US-4.6 and US-4.7) ---
    if args.check_categorisation:
        models_for_check: Dict[ClassifierType, Dict[LogicType, Any]] = (
            get_models(quick_categorisation=True)
        )
        errors = check_categorisation(
            config=config,
            models=models_for_check,
            labelled_receipts=labelled_receipts,
        )
        if errors:
            print("")
            print("=" * 60)
            print(
                f"  {len(errors)} uncategorised transaction(s) found"
            )
            print("=" * 60)
            for err in errors:
                print(str(err))
            print("=" * 60)
            sys.exit(1)
        else:
            print("All CSV transactions can be categorised.")

    if args.check_matching:
        check_matching(
            config=config,
            labelled_receipts=labelled_receipts,
        )

    # If only checks were requested, exit now.
    if args.check_categorisation or args.check_matching:
        if not any([
            args.preprocess_csvs,
            args.preprocess_assets,
            args.link_receipts_to_transactions,
            getattr(args, "match_receipts", False),
            getattr(args, "match_csv_to_csv", False),
            getattr(args, "match_transactions", False),
            args.edit_receipt,
            args.new_setup,
            args.generate_rules,
            args.tui_label_receipts,
        ]):
            return

    # --match-transactions expands into both matching sub-flags.
    if args.match_transactions:
        args.match_receipts = True
        args.match_csv_to_csv = True

    if (
        args.preprocess_csvs
        or args.preprocess_assets
        or args.link_receipts_to_transactions
        or args.match_receipts
        or args.match_csv_to_csv
    ):
        models: Dict[ClassifierType, Dict[LogicType, Any]] = get_models(
            quick_categorisation=args.quick_categorisation
        )

        # Batch-match receipts to CSV transactions BEFORE preprocessing,
        # so that withdrawal metadata is available when bank CSVs are
        # processed.
        if args.match_receipts:
            labelled_receipts = manage_batch_match_receipts(
                config=config,
                labelled_receipts=labelled_receipts,
            )

        # Reconcile linked-account CSV transactions (interactive for
        # cross-currency matches).  The suppress_ids and category_overrides
        # are passed to preprocess_generic_csvs so it doesn't re-run
        # reconciliation.
        suppress_ids: Dict = {}
        category_overrides: Dict[str, str] = {}
        if args.match_csv_to_csv:
            suppress_ids, category_overrides = manage_match_csv_to_csv(
                config=config,
                labelled_receipts=labelled_receipts,
            )

        if args.preprocess_csvs:
            manage_preprocessing_csvs(
                config=config,
                models=models,
                labelled_receipts=labelled_receipts,
                suppress_ids=suppress_ids if suppress_ids else None,
                category_overrides=category_overrides if category_overrides else None,
            )

        if args.preprocess_assets:
            manage_preprocessing_assets(
                config=config,
                models=models,
                labelled_receipts=labelled_receipts,
            )

        if args.link_receipts_to_transactions:
            manage_matching_manual_receipt_objs_to_account_transactions(
                config=config,
                models=models,
                labelled_receipts=labelled_receipts,
            )

    if args.edit_receipt:
        edit_receipt(config=config, labelled_receipts=labelled_receipts)

    if args.new_setup:
        manage_creating_new_setup(
            config=config,
            labelled_receipts=labelled_receipts,
        )

    if args.generate_rules:
        manage_generating_rules(
            config=config,
        )

    if args.tui_label_receipts:
        manage_creating_receipt_img_labels_with_tui(
            config=config, labelled_receipts=labelled_receipts, verbose=False
        )


if __name__ == "__main__":
    main()
