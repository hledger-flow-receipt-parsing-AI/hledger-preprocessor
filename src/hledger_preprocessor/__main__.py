"""Entry point for the project."""

from argparse import Namespace

from typeguard import typechecked

from hledger_preprocessor.arg_parser import (
    assert_args_are_valid,
    create_arg_parser,
)
from hledger_preprocessor.config.load_config import Config, load_config
from hledger_preprocessor.management.helper import edit_receipt
from hledger_preprocessor.management.main_manager import (
    manage_creating_new_setup,
    manage_creating_receipt_img_labels_with_tui,
    manage_generating_rules,
    manage_matching_manual_receipt_objs_to_account_transactions,
    manage_preprocessing_assets,
    manage_preprocessing_csvs,
)


@typechecked
def main() -> None:
    # Parse input arguments
    parser = create_arg_parser()

    ## NEW
    args: Namespace = parser.parse_args()
    assert_args_are_valid(args=args)
    config: Config = load_config(
        config_path=args.config,
        pre_processed_output_dir=args.pre_processed_output_dir,
    )

    if args.edit_receipt:
        edit_receipt(
            config=config,
        )

    if args.new_setup:
        manage_creating_new_setup(
            config=config,
        )

    if args.preprocess_csvs:
        manage_preprocessing_csvs(
            config=config,
            quick_categorisation=args.quick_categorisation,
        )

    if args.generate_rules:
        manage_generating_rules(
            config=config,
        )

    if args.tui_label_receipts:
        manage_creating_receipt_img_labels_with_tui(
            config=config, verbose=False
        )

    if args.link_receipts_to_transactions:
        manage_matching_manual_receipt_objs_to_account_transactions(
            config=config,
            args=args,
        )

    if args.preprocess_assets:
        manage_preprocessing_assets(
            config=config,
        )
