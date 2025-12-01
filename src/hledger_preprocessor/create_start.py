import os
import shutil
import stat
from typing import List, Tuple

from typeguard import typechecked

from hledger_preprocessor.config.AccountConfig import AccountConfig
from hledger_preprocessor.config.Config import Config
from hledger_preprocessor.dir_reading_and_writing import (
    assert_dir_exists,
    create_dir,
)
from hledger_preprocessor.file_reading_and_writing import assert_file_exists


@typechecked
def get_script_path() -> str:
    """Gets the path of the current script."""
    return os.path.dirname(os.path.abspath(__file__))


@typechecked
def export_csv_transactions_per_acount_into_each_year(  # TODO: rename the starting info.
    *,
    config: Config,
    account_config: AccountConfig,
    transaction_years: List[int],
) -> None:
    """Prompts the user for necessary information to set up the import
    directory structure.

    Returns:
      A tuple containing:
        - base_dir: The base directory for the import structure.
        - account_holder: The name of the account holder.
        - bank: The name of the bank.
        - account_type: The type of the account.
        - year: The year of the transactions.
    """

    path_to_account_type, transaction_year_paths = (
        ensure_hledger_flow_dir_structure_is_build(
            config=config,
            account_holder=account_config.account.account_holder,
            bank=account_config.account.bank,
            account_type=account_config.account.account_type,
            transaction_years=transaction_years,
        )
    )

    current_path: str = get_script_path()
    copy_file_to_target_dir(
        path_to_account_type=path_to_account_type,
        source_script_path=f"{current_path}/createRules",
    )
    copy_file_to_target_dir(
        path_to_account_type=path_to_account_type,
        source_script_path=f"{current_path}/preprocess",
    )
    for some_year_path in transaction_year_paths:
        if account_config.has_input_csv():

            csv_filepath: str = account_config.get_abs_csv_filepath(
                dir_paths_config=config.dir_paths
            )
            copy_file_to_target_dir(
                path_to_account_type=f"{some_year_path}",
                source_script_path=csv_filepath,
            )


@typechecked
def copy_file_to_target_dir(
    *, path_to_account_type: str, source_script_path: str
) -> None:
    script_filename: str = os.path.basename(source_script_path)
    assert_dir_exists(dirpath=path_to_account_type)
    assert_file_exists(filepath=source_script_path)

    # copy the script into the account holder path.
    shutil.copy(source_script_path, path_to_account_type)
    script_path: str = f"{path_to_account_type}/{script_filename}"
    assert_file_exists(filepath=script_path)

    # Ensure the script is runnable. (Like chmod +x <filename>).
    os.chmod(script_path, stat.S_IEXEC | stat.S_IREAD | stat.S_IWRITE)


@typechecked
def ensure_hledger_flow_dir_structure_is_build(
    *,
    config: Config,
    account_holder: str,
    bank: str,
    account_type: str,
    transaction_years: List[int],
) -> Tuple[str, List[str]]:
    """Creates the required directory structure for the specified account
    details.

    Args:
        root_finance_path: The root directory for finance-related files.
        account_holder: The name of the account holder.
        bank: The name of the bank.
        account_type: The type of account.

    Returns:
        The path to the "1-in" directory.
    """
    # Assert the root directory exists.
    assert os.path.exists(
        config.dir_paths.root_finance_path
    ), f"Root directory '{config.dir_paths.root_finance_path}' does not exist."

    import_path: str = config.get_import_path(assert_exists=False)
    create_dir(path=import_path)

    account_holder_path = os.path.join(import_path, account_holder)
    create_dir(path=account_holder_path)

    bank_path = os.path.join(account_holder_path, bank)
    create_dir(path=bank_path)

    account_type_path = os.path.join(bank_path, account_type)
    create_dir(path=account_type_path)

    one_in_path = os.path.join(account_type_path, "1-in")
    create_dir(path=one_in_path)

    year_paths: List[str] = []
    for transaction_year in transaction_years:
        some_year_path = os.path.join(one_in_path, str(transaction_year))
        create_dir(path=some_year_path)
        year_paths.append(some_year_path)
        # TODO: instead of creating the current year path, create the years for which transactions are included in the input csv.

    return account_type_path, list(set(year_paths))


# @typechecked
# def get_account_info_from_dir(root_dir: str) -> list[dict]:
#     """Scans the given root directory for subdirectories representing account
#     holders, banks, and account types.

#     Args:
#         root_dir: The root directory to scan.

#     Returns:
#         A list of dictionaries, each containing 'account', 'bank', and 'account_type' keys.
#     """

#     account_info = []
#     for account_holder in os.listdir(root_dir):
#         account_holder_dir = os.path.join(root_dir, account_holder)
#         if os.path.isdir(account_holder_dir):
#             for bank in os.listdir(account_holder_dir):
#                 bank_dir = os.path.join(account_holder_dir, bank)
#                 if os.path.isdir(bank_dir):
#                     for account_type in os.listdir(bank_dir):
#                         account_type_dir = os.path.join(bank_dir, account_type)
#                         if os.path.isdir(account_type_dir):
#                             account_info.append(
#                                 {
#                                     "account": account_holder,
#                                     "bank": bank,
#                                     "account_type": account_type,
#                                 }
#                             )
#     return account_info
