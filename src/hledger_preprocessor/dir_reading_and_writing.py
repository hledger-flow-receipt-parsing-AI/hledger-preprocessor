"""Handles directory reading and writing."""

import os
import shutil
from typing import List

from typeguard import typechecked

from hledger_preprocessor.config.load_config import Config
from hledger_preprocessor.file_reading_and_writing import get_image_hash
from hledger_preprocessor.helper import (
    assert_bank_to_account_args_are_valid,
    assert_dir_exists,
)
from hledger_preprocessor.TransactionObjects.Account import Account
from hledger_preprocessor.TransactionObjects.AssetType import AssetType


@typechecked
def assert_dir_full_hierarchy_exists(
    *, config: Config, account: Account, working_subdir: str
) -> str:

    # First verify the input arguments are valid.
    assert_bank_to_account_args_are_valid(account=account)

    import_path: str = config.get_import_path(assert_exists=True)
    account_holder_path: str = f"{import_path}/{account.account_holder}"
    bank_path: str = f"{account_holder_path}/{account.bank}"

    # Deliberately verbose for readability.
    account_type_path: str = (
        f"{import_path}/{account.account_holder}/{account.bank}/"
        + f"{account.account_type}"
    )

    assert_dir_exists(dirpath=working_subdir)
    assert_dir_exists(dirpath=import_path)
    assert_dir_exists(dirpath=account_holder_path)
    assert_dir_exists(dirpath=bank_path)
    assert_dir_exists(dirpath=account_type_path)
    return account_type_path


@typechecked
def path_exists(*, path: str) -> bool:
    """Check if a given path exists."""
    return os.path.exists(path)


@typechecked
def create_year_directory(base_path: str, year: int) -> str:
    """Create a directory for the given year under base_path."""
    year_path = os.path.join(base_path, str(year))
    os.makedirs(year_path, exist_ok=True)
    assert_dir_exists(dirpath=year_path)
    return year_path


@typechecked
def generate_bank_csv_output_path(
    *,
    config: Config,
    account: Account,
    pre_processed_output_dir: str,
    year: int,
    csv_filename: str,
) -> str:
    """Generate the output path, ensure necessary directories exist."""

    if pre_processed_output_dir is None:
        raise ValueError("pre_processed_output_dir cannot be None, but it is.")

    import_path: str = config.get_import_path(assert_exists=False)
    if (
        account.account_holder is None
        or account.bank is None
        or account.account_type is None
    ):
        raise ValueError(
            f"account_holder:{account.account_holder}, bank:{account.bank}, or"
            f" account_type:{account.account_type} cannot be None, but at least"
            " 1 is."
        )
    base_path = (
        f"{import_path}/{account.account_holder}/"
        + f"{account.bank}/{account.account_type}/{pre_processed_output_dir}"
    )

    if not path_exists(path=base_path):
        os.makedirs(base_path, exist_ok=True)
        assert_dir_exists(dirpath=base_path)
    return f"{create_year_directory(base_path, year)}/{csv_filename}"


def ensure_asset_path_is_created(
    *,
    config: Config,
) -> str:
    asset_path: str = config.get_asset_path(assert_exists=False)
    if not path_exists(path=asset_path):
        os.makedirs(asset_path, exist_ok=True)
        assert_dir_exists(dirpath=asset_path)
        print(f"Creatied an asset_path at{asset_path}")
    return asset_path


# def ensure_asset_path_include_file_is_created(
#     *, config: Config, year: int
# ) -> str:
#     asset_path: str = config.get_asset_path(assert_exists=False)
#     input(f"asset_path={asset_path}")
#     f"include assets/{year}/currency.{currency}.csv"
#     if not path_exists(path=asset_path):
#         os.makedirs(asset_path, exist_ok=True)
#         assert_dir_exists(dirpath=asset_path)
#         print(f"Creatied an asset_path at{asset_path}")
#     return asset_path


@typechecked
def get_asset_csv_output_path(
    *,
    asset_path: str,
    account: Account,
    year: int,
    csv_filename: str,
) -> str:
    """Generate the output path, ensure necessary directories exist."""

    if account.asset_type != AssetType.ASSET:
        raise ValueError(
            "Expected found asset transaction to be of type asset."
        )
    if account.asset_category is None:
        raise ValueError(
            f"asset_category:{account.asset_category},cannot be None, but"
            " it is."
        )
    if year is None:
        raise ValueError(f"year:{year},cannot be None, but it is.")

    if not path_exists(path=asset_path):
        raise FileNotFoundError(f"Did not find {asset_path}")

    abs_csv_filepath: str = (
        f"{create_year_directory(asset_path, year)}/{csv_filename}"
    )
    return abs_csv_filepath


@typechecked
def create_dir(*, path: str) -> None:
    """Creates a directory at the specified path.

    Args:
        path: The path to the directory to create.

    Raises:
        FileNotFoundError: If the parent directory does not exist.
    """
    assert os.path.exists(
        os.path.dirname(path)
    ), f"Parent directory '{os.path.dirname(path)}' does not exist."
    os.makedirs(path, exist_ok=True)
    assert os.path.isdir(path), f"Failed to create directory '{path}'"


@typechecked
def create_next_dir(*, working_subdir: str, next_dir: str) -> str:
    next_path: str = os.path.join(working_subdir, next_dir)
    create_dir(path=next_path)
    return next_path


@typechecked
def create_image_folder(
    *, dataset_path: str, cropped_receipt_img_filepath: str
) -> str:
    receipt_folder_name: str = get_receipt_folder_name(
        cropped_receipt_img_filepath=cropped_receipt_img_filepath
    )
    return create_next_dir(
        working_subdir=dataset_path, next_dir=receipt_folder_name
    )


@typechecked
def get_receipt_folder_name(*, cropped_receipt_img_filepath: str) -> str:
    # Create the image folder.
    image_hash: str = get_image_hash(image_path=cropped_receipt_img_filepath)
    # creation_time = os.path.getctime(
    #     cropped_receipt_img_filepath
    # )  # This returns a float (timestamp)

    # The key change is here: Convert the creation time to a datetime object FIRST
    # dt_object = datetime.fromtimestamp(creation_time)
    # timestamp: str = (
    #     f"{dt_object.year}-{dt_object.month}-{dt_object.day}_{dt_object.hour}:{dt_object.minute}:{dt_object.microsecond}"
    # )
    # receipt_folder_name: str = f"{timestamp}_{image_hash}"
    return image_hash


@typechecked
def find_receipt_folder_path(
    *, dataset_path: str, cropped_receipt_img_filepath: str
) -> str:
    image_hash: str = get_image_hash(image_path=cropped_receipt_img_filepath)
    matching_dirs: List[str] = [
        os.path.join(dataset_path, d)
        for d in os.listdir(dataset_path)
        if os.path.isdir(os.path.join(dataset_path, d))
        and d.endswith("_" + image_hash)
    ]

    valid_dirs = []
    for dir_path in matching_dirs:
        label_filepath = os.path.join(
            dir_path, "receipt_image_to_obj_label.json"
        )
        if os.path.isfile(label_filepath):
            valid_dirs.append(dir_path)

    if len(valid_dirs) == 1:
        for dir_path in matching_dirs:
            if dir_path != valid_dirs[0]:
                shutil.rmtree(dir_path)
        return valid_dirs[0]
    elif len(valid_dirs) == 0:
        return create_image_folder(
            dataset_path=dataset_path,
            cropped_receipt_img_filepath=cropped_receipt_img_filepath,
        )
    else:
        print("")
        for valid_dir in valid_dirs:
            print(valid_dir)
        raise ValueError(
            "Multiple valid folders with label file found for hash"
            f" {image_hash}. See above."
        )
