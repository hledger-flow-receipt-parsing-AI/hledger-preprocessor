# Type alias for clarity
from dataclasses import dataclass
from typing import List, Optional, Tuple

from typeguard import typechecked

from hledger_preprocessor.config.DirPathsConfig import DirPathsConfig
from hledger_preprocessor.TransactionObjects.Account import Account

ColumnNames = List[Tuple[str, str]]
# Type alias for clarity: (Python field name, hledger field name)
ColumnNames = List[Tuple[str, str]]


@dataclass(frozen=True, unsafe_hash=True)
class CsvColumnMapping:
    """Stores the implicit order of CSV columns."""

    # Example: [['the_date', "date"], ['None', ''], ['amount_out_account', 'amount0'], ...]
    csv_column_mapping: ColumnNames


@dataclass(frozen=True, unsafe_hash=True)
class AccountConfig:
    account: Account
    input_csv_filename: Optional[str]
    csv_column_mapping: Optional[CsvColumnMapping]  # = field(default=None)

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
