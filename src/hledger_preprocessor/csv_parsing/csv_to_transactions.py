from typing import Dict, List

from hledger_core.csv_parsing.bank_csv import load_bank_transactions
from typeguard import typechecked

from hledger_preprocessor.config.AccountConfig import AccountConfig
from hledger_preprocessor.config.Config import Config
from hledger_preprocessor.csv_parsing.read_csv_asset_transactions import (
    read_csv_to_asset_transactions,
)
from hledger_preprocessor.file_reading_and_writing import assert_file_exists
from hledger_preprocessor.generics.Transaction import Transaction
from hledger_preprocessor.TransactionObjects.ProcessedTransaction import (
    ProcessedTransaction,
)
from hledger_preprocessor.TransactionObjects.Receipt import Receipt


# account_config.get_abs_csv_filepath(dir_paths_config=config.dir_paths)
@typechecked
def load_csv_transactions_from_file_per_year(
    *,
    config: Config,
    labelled_receipts: List[Receipt],
    abs_csv_filepath: str,
    account_config: AccountConfig,
    csv_encoding: str,
) -> Dict[int, List[Transaction]]:
    transactions_per_year: Dict[int, List[Transaction]] = csv_to_transactions(
        config=config,
        labelled_receipts=labelled_receipts,
        input_csv_filepath=abs_csv_filepath,
        csv_encoding=csv_encoding,
        account_config=account_config,
    )
    return transactions_per_year


@typechecked
def csv_to_transactions(
    *,
    config: Config,
    labelled_receipts: List[Receipt],
    input_csv_filepath: str,
    csv_encoding: str,
    account_config: AccountConfig,
) -> Dict[int, List["Transaction"]]:
    """Process transactions from a CSV file: convert encoding, parse, and
    sort by year."""
    assert_file_exists(filepath=input_csv_filepath)

    total_transactions: List[Transaction] = parse_encoded_input_csv(
        config=config,
        labelled_receipts=labelled_receipts,
        input_csv_filepath=input_csv_filepath,
        account_config=account_config,
    )

    transactions_per_year: Dict[int, List[Transaction]] = (
        sort_transactions_on_years(transactions=total_transactions)
    )

    return transactions_per_year


@typechecked
def sort_transactions_on_years(
    *, transactions: List[Transaction]
) -> Dict[int, List[Transaction]]:
    years = get_years(transactions=transactions)
    return {
        year: [t for t in transactions if t.get_year() == year]
        for year in years
    }


@typechecked
def parse_encoded_input_csv(
    *,
    config: Config,
    labelled_receipts: List[Receipt],
    input_csv_filepath: str,
    account_config: AccountConfig,
) -> List[Transaction]:
    """A bank account's export (delimiter and header from the account
    config), or the asset CSV of an account without an export."""
    if account_config.has_input_csv():
        return load_bank_transactions(
            account_config=account_config,
            abs_csv_filepath=input_csv_filepath,
            csv_encoding=config.csv_encoding,
        )

    csv_output_filepath: str = account_config.get_abs_csv_filepath(
        dir_paths_config=config.dir_paths
    )
    csv_asset_transactions: List[ProcessedTransaction] = (
        read_csv_to_asset_transactions(
            csv_filepath=csv_output_filepath,
            labelled_receipts=labelled_receipts,
        )
    )
    return list(map(lambda txn: txn.transaction, csv_asset_transactions))


@typechecked
def get_years(*, transactions: List[Transaction]) -> List[int]:
    years: List[int] = [transaction.get_year() for transaction in transactions]
    return years
