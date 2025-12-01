from typing import Dict, List

from typeguard import typechecked

from hledger_preprocessor.config.load_config import Config
from hledger_preprocessor.csv_parsing.csv_to_transactions import (
    load_csv_transactions_from_file_per_year,
)
from hledger_preprocessor.Currency import (
    Transactions,
)
from hledger_preprocessor.receipt_transaction_matching.get_bank_data_from_transactions import (
    HledgerFlowAccountInfo,
    get_account_info_groups_from_years,
)


# Action 0.
@typechecked
def get_all_accounts(
    *, config: Config, transactions_type: Transactions
) -> set[HledgerFlowAccountInfo]:

    all_accounts: set[HledgerFlowAccountInfo] = set()
    # Step 3: Label images and get receipt objects
    for account_config in config.accounts:

        transactions_per_year_per_account: Dict[int, List[Transaction]] = (
            load_csv_transactions_from_file_per_year(
                abs_csv_filepath=account_config.get_abs_csv_filepath(
                    dir_paths_config=config.dir_paths
                ),
                transactions_type=transactions_type,
                account_config=account_config,
                csv_encoding=config.csv_encoding,
            )
        )
        accounts_in_those_transactions: set[HledgerFlowAccountInfo] = set(
            get_account_info_groups_from_years(
                transactions_per_year=transactions_per_year_per_account
            )
        )
        # Update means merge.
        all_accounts.update(accounts_in_those_transactions)
    return all_accounts
