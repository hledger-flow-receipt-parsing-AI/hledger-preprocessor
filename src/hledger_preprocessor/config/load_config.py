import os
from pathlib import Path
from pprint import pprint
from typing import Any, Optional, Union

import yaml
from typeguard import typechecked

from hledger_preprocessor.arg_parser import assert_has_only_valid_chars
from hledger_preprocessor.config.Config import Config
from hledger_preprocessor.file_reading_and_writing import assert_file_exists
from hledger_preprocessor.helper import assert_dir_exists


@typechecked
def verify_matching_algo(*, matching_algo: dict[str, Any]) -> dict[str, Any]:
    """Verifies the matching_algo configuration."""
    required_fields = [
        "days",
        "amount_range",
        "days_month_swap",
        "multiple_receipts_per_transaction",
    ]
    for field in required_fields:
        if field not in matching_algo or matching_algo[field] is None:
            raise ValueError(f"Missing required matching_algo field: {field}")

    # Verify types and constraints
    if not isinstance(matching_algo["days"], int) or matching_algo["days"] < 0:
        raise ValueError("matching_algo.days must be a non-negative integer")
    if (
        not isinstance(matching_algo["amount_range"], (int, float))
        or matching_algo["amount_range"] < 0
    ):
        raise ValueError(
            "matching_algo.amount_range must be a non-negative number"
        )
    if not isinstance(matching_algo["days_month_swap"], bool):
        raise ValueError("matching_algo.days_month_swap must be a boolean")
    if not isinstance(matching_algo["multiple_receipts_per_transaction"], bool):
        raise ValueError(
            "matching_algo.multiple_receipts_per_transaction must be a boolean"
        )
    return matching_algo


@typechecked
def verify_config(*, config: dict[str, Any]) -> dict[str, Any]:
    # Verify required top-level fields
    required_fields = [
        "account_configs",
        "dir_paths.root_finance_path",
        "dir_paths.working_subdir",
        "file_names.start_journal_filepath",
        "matching_algo",
    ]
    for field in required_fields:
        keys = field.split(".")
        value = config
        for key in keys:
            value = value.get(key)
            if value is None:
                raise ValueError(f"Missing required config field: {field}")

    assert_dir_exists(
        dirpath=config.get("dir_paths", {}).get("root_finance_path")
    )
    # Verify directory paths
    for dir_name_description in [
        # "root_finance_path", # Is absolute
        "receipt_images_input_dir",  # Is relative_dir_name
        "receipt_labels_dir",
    ]:
        if dir_name := config.get("dir_paths", {}).get(dir_name_description):
            assert_dir_exists(
                dirpath=f'{config["dir_paths"]["root_finance_path"]}/{dir_name}'
            )

    # Verify each account in the accounts list
    for account_config in config["account_configs"]:
        req_account_conf_fields = [
            "input_csv_filename",
            "account_holder",
            "bank",
            "account_type",
        ]
        for field in req_account_conf_fields:
            if field not in account_config:
                raise ValueError(f"Missing required account field: {field}")

            if field != "input_csv_filename" and account_config[field] is None:
                raise ValueError(f"Missing required account field: {field}")

        # Validate string fields for valid characters
        assert_has_only_valid_chars(
            input_string=account_config["account_holder"]
        )
        assert_has_only_valid_chars(input_string=account_config["bank"])
        assert_has_only_valid_chars(input_string=account_config["account_type"])

        # Verify input_csv_filename exists
        # if account
        if account_config["input_csv_filename"] not in ["None", "", None]:
            input_csv_filepath: str = (
                f'{config["dir_paths"]["root_finance_path"]}/{account_config["input_csv_filename"]}'
            )
            assert_file_exists(filepath=input_csv_filepath)

    # Verify file paths
    for file_name_description in ["start_journal_filepath"]:
        if file_name := config.get("file_paths", {}).get(file_name_description):
            assert_file_exists(
                filepath=file_name
            )  # TODO: double check what this should be.

    # Validate receipts and dataset path dependency
    if config.get("dir_paths", {}).get(
        "receipt_images_input_dir"
    ) and not config.get("dir_paths", {}).get("receipt_labels_dir"):
        raise ValueError(
            "If receipt_images_input_dir is provided, receipt_labels_dir is"
            " required."
        )

    # Verify matching_algo
    verify_matching_algo(matching_algo=config["matching_algo"])

    return config


@typechecked
def load_config(
    *,
    config_path: str,
    pre_processed_output_dir: Union[None, str],
    verbose: Optional[bool] = False,
) -> Config:
    assert_file_exists(filepath=config_path)
    with open(config_path) as file:
        config_dict = yaml.safe_load(file)
    verified_config = verify_config(config=config_dict)
    if pre_processed_output_dir is not None:
        verified_config["dir_paths"][
            "pre_processed_output_dir"
        ] = pre_processed_output_dir

    config = Config.from_dict(config_dict=verified_config)
    if verbose:
        print(f"✅ ABS_ASSET_PATH exported: {os.environ.get('ABS_ASSET_PATH')}")
    return config


@typechecked
def load_config(
    *,
    config_path: str,
    pre_processed_output_dir: Union[None, str],
    verbose: Optional[bool] = False,
) -> Config:
    assert_file_exists(filepath=config_path)
    with open(config_path) as file:
        config_dict = yaml.safe_load(file)
    verified_config = verify_config(config=config_dict)
    if pre_processed_output_dir is not None:
        verified_config["dir_paths"][
            "pre_processed_output_dir"
        ] = pre_processed_output_dir
        if verbose:
            print("verified_config=")
            pprint(verified_config)
    return Config.from_dict(
        config_dict=verified_config,
    )


@typechecked
def raw_receipt_img_filepath_to_cropped(
    *, config: Config, raw_receipt_img_filepath: str
) -> str:
    # Extract the filename stem from the raw receipt image filepath
    filename_stem = Path(raw_receipt_img_filepath).stem
    # Construct the cropped filename using the crop suffix and extension from config
    cropped_filename = f"{filename_stem}{config.file_names.receipt_img.crop}{config.file_names.receipt_img.crop_ext}"
    # Join with the processed images directory to get the full path
    cropped_filepath = os.path.join(
        config.dir_paths.get_path(
            "receipt_images_processed_dir", absolute=True
        ),
        cropped_filename,
    )
    return cropped_filepath
