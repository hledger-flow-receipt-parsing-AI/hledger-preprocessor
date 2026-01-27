"""Entry point for the project."""

from argparse import Namespace
from typing import Any, Dict, List

from typeguard import typechecked

from hledger_preprocessor.arg_parser import (
    assert_args_are_valid,
    create_arg_parser,
)
from hledger_preprocessor.config.load_config import Config, load_config
from hledger_preprocessor.generics.enums import ClassifierType, LogicType
from hledger_preprocessor.get_models import get_models
from hledger_preprocessor.management.helper import edit_receipt
from hledger_preprocessor.management.main_manager import (
    manage_creating_new_setup,
    manage_creating_receipt_img_labels_with_tui,
    manage_generating_rules,
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
    print(f"DEBUG: args parsed, link_receipts_to_transactions={args.link_receipts_to_transactions}")
    assert_args_are_valid(args=args)
    config: Config = load_config(
        config_path=args.config,
        pre_processed_output_dir=args.pre_processed_output_dir,
    )
    print("DEBUG: config loaded")

    labelled_receipts: List[Receipt] = load_receipts_from_dir(config=config)
    print(f"DEBUG: loaded {len(labelled_receipts)} receipts from dir")

    if (
        args.preprocess_csvs
        or args.preprocess_assets
        or args.link_receipts_to_transactions
    ):
        print("DEBUG: entering models/matching block")
        models: Dict[ClassifierType, Dict[LogicType, Any]] = get_models(
            quick_categorisation=args.quick_categorisation
        )
        print("DEBUG: models loaded")

        if args.preprocess_csvs:
            manage_preprocessing_csvs(
                config=config,
                models=models,
                labelled_receipts=labelled_receipts,
            )

        if args.preprocess_assets:
            manage_preprocessing_assets(
                config=config,
                models=models,
                labelled_receipts=labelled_receipts,
            )

        if args.link_receipts_to_transactions:
            print("DEBUG: calling manage_matching_manual_receipt_objs_to_account_transactions")
            manage_matching_manual_receipt_objs_to_account_transactions(
                config=config,
                models=models,
                labelled_receipts=labelled_receipts,
            )
            print("DEBUG: finished manage_matching_manual_receipt_objs_to_account_transactions")

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
            config=config, verbose=False
        )


if __name__ == "__main__":
    main()
