import os
from typing import Dict, List

from typeguard import typechecked

from hledger_preprocessor.categorisation.categoriser import (
    classify_transactions,
)
from hledger_preprocessor.config.AccountConfig import AccountConfig
from hledger_preprocessor.config.load_config import (
    Config,
)
from hledger_preprocessor.csv_parsing.export_to_csv import write_processed_csv
from hledger_preprocessor.dir_reading_and_writing import (
    generate_bank_csv_output_path,
)
from hledger_preprocessor.generics.Transaction import Transaction


@typechecked
def pre_process_csvs(
    *,
    # args: Namespace,
    config: Config,
    account_config: AccountConfig,
    transactions_per_year: Dict[int, List[Transaction]],
    ai_models_tnx_classification: List,
    rule_based_models_tnx_classification: List,
) -> None:
    """
    Create one pre-processed CSV file per year for the given account.

    Output structure:
      - A directory defined by config.dir_paths["pre_processed_output_dir"].
      - Inside it, one CSV per year:
            {account_name}/{year}/{original_csv_filename}
        where:
            account_name comes from account_config.account
            year is the transaction year key
            original_csv_filename is the basename of the source CSV file

    Each generated CSV contains:
      - All transactions for that year
      - Additional fields produced by classification:
            • AI-based classification results
            • Rule-based classification results

    The function validates that the output directory path is non-null,
    classifies transactions using both model sets, and writes the
    processed CSVs to the computed output paths.
    """

    # TODO: assert all trannsaction hashes are unique.

    if config.dir_paths.get_path("pre_processed_output_dir", absolute=True) in [
        None,
        "None",
    ]:
        raise ValueError(
            "config.dir_paths.get_path('pre_processed_output_dir,absolute=True"
            " ) cannot be None, but it is"
        )

    # Output the pre-processed .csv files per year.
    for year, transactions in transactions_per_year.items():
        output_filepath: str = generate_bank_csv_output_path(
            config=config,
            account=account_config.account,
            pre_processed_output_dir=config.dir_paths.get_path(
                "pre_processed_output_dir", absolute=False
            ),
            year=year,
            csv_filename=os.path.basename(
                account_config.get_abs_csv_filepath(
                    dir_paths_config=config.dir_paths
                )
            ),
        )

        classified_transactions: List[Transaction] = classify_transactions(
            transactions=transactions,
            ai_models_tnx_classification=ai_models_tnx_classification,
            rule_based_models_tnx_classification=rule_based_models_tnx_classification,
            category_namespace=config.category_namespace,
        )
        print(f"outputting CSV to:{output_filepath}")
        write_processed_csv(
            transactions=classified_transactions,
            account_config=account_config,
            filepath=output_filepath,
        )
