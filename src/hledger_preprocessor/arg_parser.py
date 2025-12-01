"""Parses the CLI args."""

import argparse
import re

from typeguard import typechecked


@typechecked
def create_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Convert Triodos Bank CSV to custom format."
    )

    # Data arguments
    parser.add_argument(
        "-p",
        "--pre-processed-output-dir",
        type=str,
        required=False,
        help="The dir name containing the pre-processed csv files..",
    )

    parser.add_argument(
        "-c",
        "--config",
        type=str,
        required=False,
        help="Path to config file.",
    )

    parser.add_argument(
        "-e",
        "--edit-receipt",
        action="store_true",
        required=False,
        help="Edit a receipt in TUI.",
    )

    # Action arguments
    # Action 0.
    parser.add_argument(
        "-n",
        "--new-setup",
        action="store_true",
        required=False,
        help=(
            "Use this flag if you want to add a new account for double-entry"
            " book keeping."
        ),
    )

    # Action 1.
    parser.add_argument(
        "-o",
        "--preprocess-csvs",
        action="store_true",
        required=False,
        help=(
            "Convert the csv from the bank to csvs that hledger-flow can read."
        ),
    )

    # Action 2.
    parser.add_argument(
        "-r",
        "--generate-rules",
        required=False,
        action="store_true",
        help="Generates the .rules file for hledger flow imports.",
    )

    # Action 3.a
    parser.add_argument(
        "-t",
        "--tui-label-receipts",
        action="store_true",
        required=False,
        help=(
            "Manually make the labels for the receipt images that do not have a"
            " manual label yet."
        ),
    )

    # Action 3.b
    parser.add_argument(
        "-a",
        "--make-ai-labels",
        action="store_true",
        required=False,
        help=(
            "Use AI models to convert the  receipt images into Receipt objects"
            " for receipt images that do not have an AI label yet."
        ),
    )

    # Action 3.c
    parser.add_argument(
        "-i",
        "--improve-manual-labels",
        action="store_true",
        required=False,
        help=(
            "Manually improve the existing manual labels for the receipt"
            " images."
        ),
    )

    # Action 4.
    parser.add_argument(
        "-l",
        "--link-receipts-to-transactions",
        action="store_true",
        required=False,
        help=(
            "Link the receipt images to the accompanying (if any) transaction"
            " of your bank csv to prevent duplicate entries. Can only be done"
            " after .csv pre-processing and after all receipt images are"
            " converted to receipt objects."
        ),
    )
    parser.add_argument(
        "-s",
        "--preprocess-assets",
        action="store_true",
        required=False,
        help="Make hledger-flow preprocess the exported asset csvs.",
    )

    # Debugging functionality.
    parser.add_argument(
        "-q",
        "--quick-categorisation",
        action="store_true",
        required=False,
        help=(
            "Quickly get feedback on unidentified transactions to quickly"
            " create (private) categorisation rules."
        ),
    )

    return parser


def assert_has_only_valid_chars(*, input_string: str) -> None:
    # a-Z, underscore, \, /.
    valid_chars = re.compile(r"^[a-zA-Z0-9_/\\]*$")
    assert valid_chars.match(
        input_string
    ), f"Invalid characters found in: {input_string}"


@typechecked
def assert_args_are_valid(*, args: argparse.Namespace) -> None:
    if args.quick_categorisation:
        if not args.preprocess_csvs:
            raise ValueError(
                "To quickly create new .csv transaction categorisation rules,"
                " you need to include the --preprocess-csvs arg and the"
                " --pre-processed-output-dir."
            )
    if args.preprocess_csvs:
        if args.pre_processed_output_dir is None:
            raise ValueError(
                "The pre_processed_output_dir arg is required for"
                " preprocess_csvs."
            )
