# Type alias for clarity
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Tuple

from typeguard import typechecked

from hledger_preprocessor.config.CsvColumnMapping import CsvColumnMapping
from hledger_preprocessor.config.DirPathsConfig import DirPathsConfig
from hledger_preprocessor.generics.GenericTransactionWithCsv import (
    GenericCsvTransaction,
)
from hledger_preprocessor.TransactionObjects.Account import Account
from hledger_preprocessor.TransactionObjects.AccountTransaction import (
    AccountTransaction,
)


@dataclass(frozen=True)
class SplitGroup:
    """A group of row-type values that share the same column mapping."""
    values: Tuple[str, ...]
    csv_column_mapping: CsvColumnMapping
    tnx_date_columns: CsvColumnMapping


@dataclass(frozen=True)
class LinkedAccount:
    """A reference to another tracked account that transacts with this one."""
    account_holder: str
    bank: str
    account_type: str
    transfer_types: Tuple[str, ...]  # split group values to suppress, empty = none


@dataclass(frozen=True, unsafe_hash=True)
class AccountConfig:
    account: Account
    input_csv_filename: Optional[str]
    csv_column_mapping: Optional[CsvColumnMapping]  # = field(default=None)
    tnx_date_columns: Optional[CsvColumnMapping]  # = field(default=None)

    # Split-by-type: logically split a single CSV into groups with
    # different column mappings based on values in one column.
    split_column: Optional[int] = None
    split_groups: Optional[Tuple[SplitGroup, ...]] = None

    # Decimal format: "eu" (1.234,56) or "dot" (1,234.56) or None (legacy=eu)
    decimal_format: Optional[str] = None

    # Linked accounts: other tracked accounts that transact with this one
    linked_accounts: Optional[Tuple[LinkedAccount, ...]] = None

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
            asset_path: str = dir_paths_config.get_path(
                path_name="asset_transaction_csvs_dir", absolute=True
            )
            return f"{asset_path}/{self.account.account_holder}/{self.account.bank}/{self.account.account_type}/{self.account.base_currency}.csv"
            # return f"{dir_paths_config.root_finance_path}/{dir_paths_config.asset_transaction_csvs_dir}/{self.account.account_holder}/{self.account.bank}/{self.account.account_type}/{self.account.base_currency}.csv"

    @typechecked
    def get_hledger_csv_column_names(self) -> List[str]:

        if self.has_input_csv():
            # In split mode csv_column_mapping is None; use first group's.
            mapping = self.csv_column_mapping
            if (mapping is None or mapping.csv_column_mapping is None) and self.split_groups:
                mapping = self.split_groups[0].csv_column_mapping
            dummy_csv_tnx: GenericCsvTransaction = GenericCsvTransaction(
                the_date=datetime.now(),
                account=self.account,
                tendered_amount_out=1,  # TODO: don't use this hardcoding.
                change_returned=0,  # TODO: don't use this hardcoding.
            )
            return list(
                dummy_csv_tnx.to_hledger_dict(
                    csv_column_mapping=mapping
                ).keys()
            )
            # return self.csv_column_mapping.get_hledger_csv_column_names()
        else:
            dummy_account_tnx: AccountTransaction = AccountTransaction(
                the_date=datetime.now(),
                account=self.account,
                tendered_amount_out=1,  # TODO: don't use this hardcoding.
                change_returned=0,  # TODO: don't use this hardcoding.
            )
            return list(dummy_account_tnx.to_hledger_dict().keys())
            # return (
            #     dummy_account_tnx.csv_column_mapping.get_hledger_csv_column_names()
            # )

    @typechecked
    def parse_csv_rows(
        self,
        *,
        rows: List[List[str]],
        start_index: int,
    ) -> List[GenericCsvTransaction]:
        """Parse CSV rows, handling split-by-type when configured.

        When split_column is set, each row is routed to the SplitGroup
        whose values contain the row's type, and that group's
        csv_column_mapping is used.  Otherwise the single
        csv_column_mapping on this AccountConfig is used for all rows.

        Returns a flat list of GenericCsvTransaction (preserving order).
        """
        from hledger_preprocessor.generics.parse_generic_tnx_with_csv import (
            parse_generic_bank_transaction,
        )

        transactions: List[GenericCsvTransaction] = []

        if self.split_column is not None and self.split_groups:
            # Build value→group lookup
            value_to_group = {}
            for group in self.split_groups:
                for val in group.values:
                    value_to_group[val] = group

            for index in range(start_index, len(rows)):
                row = rows[index]
                if self.split_column >= len(row):
                    continue
                row_type = row[self.split_column].strip()
                group = value_to_group.get(row_type)
                if group is None:
                    raise ValueError(
                        f"Row {index}: type '{row_type}' not covered by "
                        f"any split group. Known types: "
                        f"{sorted(value_to_group.keys())}"
                    )
                transaction = parse_generic_bank_transaction(
                    row=row,
                    nr_in_batch=index,
                    account_config=self,
                    csv_column_mapping=group.csv_column_mapping,
                )
                transaction.extra["_row_type"] = row_type
                transactions.append(transaction)
        else:
            for index in range(start_index, len(rows)):
                transaction = parse_generic_bank_transaction(
                    row=rows[index],
                    nr_in_batch=index,
                    account_config=self,
                    csv_column_mapping=self.csv_column_mapping,
                )
                transactions.append(transaction)

        return transactions
