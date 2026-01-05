from typing import Dict, List

from typeguard import typechecked

from hledger_preprocessor.config.AccountConfig import AccountConfig
from hledger_preprocessor.config.Config import Config
from hledger_preprocessor.create_start import (
    copy_file_to_target_dir,
    ensure_hledger_flow_dir_structure_is_build,
    get_script_path,
)
from hledger_preprocessor.csv_parsing.export_to_csv import (
    write_asset_transaction_to_csv,
)
from hledger_preprocessor.dir_reading_and_writing import (
    assert_dir_full_hierarchy_exists,
)
from hledger_preprocessor.rules.generate_rules_content import (
    generate_rules_file,
)
from hledger_preprocessor.TransactionObjects.ProcessedTransaction import (
    ProcessedTransaction,
)
from hledger_preprocessor.TransactionObjects.Receipt import Receipt


@typechecked
def output_non_input_csv_transactions(  # TODO: rename the starting info.
    *,
    config: Config,
    labelled_receipts: List[Receipt],
    non_input_csv_transactions: Dict[AccountConfig, List[ProcessedTransaction]],
    # transaction_years: List[int],
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

    for account_config, transactions in non_input_csv_transactions.items():
        if transactions:
            years: set[int] = set()
            for tnx in transactions:
                # if tnx.tendered_amount_out == float(350):
                # years.add(tnx.parent_receipt.get_year())
                years.add(int(tnx.transaction.the_date.strftime("%Y")))

            path_to_account_type, transaction_year_paths = (
                ensure_hledger_flow_dir_structure_is_build(
                    config=config,
                    account_holder=account_config.account.account_holder,
                    bank=account_config.account.bank,
                    account_type=account_config.account.account_type,
                    transaction_years=list(years),
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

            if account_config.has_input_csv():
                raise ValueError("Should not have input csv filepath specified")
            else:
                csv_output_filepath: str = account_config.get_abs_csv_filepath(
                    dir_paths_config=config.dir_paths
                )

                for tnx in transactions:
                    if not isinstance(tnx, ProcessedTransaction):
                        raise TypeError(
                            f"Expected ProcessedTransaction, got:{tnx}"
                        )

                    write_asset_transaction_to_csv(
                        config=config,
                        labelled_receipts=labelled_receipts,
                        transaction=tnx,
                        filepath=csv_output_filepath,
                        account_config=account_config,
                    )

                for some_year_path in transaction_year_paths:
                    copy_file_to_target_dir(
                        path_to_account_type=f"{some_year_path}",
                        source_script_path=csv_output_filepath,
                    )

            assert_dir_full_hierarchy_exists(
                config=config,
                account=account_config.account,
                working_subdir=config.get_working_subdir_path(
                    assert_exists=False
                ),
            )
            generate_rules_file(
                config=config,
                account_config=account_config,
                # example_transaction=transactions[0],
            )
