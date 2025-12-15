# Type alias for clarity
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

from typeguard import typechecked

from hledger_preprocessor.config.CsvColumnMapping import CsvColumnMapping
from hledger_preprocessor.config.DirPathsConfig import DirPathsConfig
from hledger_preprocessor.TransactionObjects.Account import Account
from hledger_preprocessor.TransactionObjects.AccountTransaction import (
    AccountTransaction,
)


@dataclass(frozen=True, unsafe_hash=True)
class AccountConfig:
    account: Account
    input_csv_filename: Optional[str]
    csv_column_mapping: Optional[CsvColumnMapping]  # = field(default=None)
    tnx_date_columns: Optional[CsvColumnMapping]  # = field(default=None)

    # Field exists, no default, not part of __init__

    def __post_init__(self):
        if not isinstance(self.account, Account):
            raise TypeError(
                f"Account should be of type Account. Got:{self.account}"
            )

    @typechecked
    def has_input_csv(self) -> bool:
        if self.input_csv_filename:

            if isinstance(self.input_csv_filename, str):
                if self.input_csv_filename.endswith(".csv"):
                    return True
                return False
            else:
                raise TypeError(
                    "Unexpected not get input_csv_filename"
                    f" type:{type(self.input_csv_filename)}"
                )
        return False

    @typechecked
    def get_abs_csv_filepath(self, dir_paths_config: DirPathsConfig) -> str:
        # return f"{dir_paths_config.root_finance_path}/{self.input_csv_filename}"
        if self.has_input_csv():
            if not self.input_csv_filename.startswith(
                dir_paths_config.root_finance_path
            ):
                return f"{dir_paths_config.root_finance_path}/{self.input_csv_filename}"
            return self.input_csv_filename
        else:
            return f"{dir_paths_config.root_finance_path}/{dir_paths_config.asset_transaction_csvs_dir}/{self.account.account_holder}/{self.account.bank}/{self.account.account_type}/{self.account.base_currency}.csv"

    @typechecked
    def get_hledger_csv_column_names(self) -> List[str]:

        if self.has_input_csv():
            return self.csv_column_mapping.get_hledger_csv_column_names()
        else:
            dummy_account_tnx: AccountTransaction = AccountTransaction(
                the_date=datetime.now(),
                account=self.account,
                currency=self.account.base_currency,
                amount_out_account=1,  # TODO: don't use this hardcoding.
                change_returned=0,  # TODO: don't use this hardcoding.
            )
            return (
                dummy_account_tnx.csv_column_mapping.get_hledger_csv_column_names()
            )
