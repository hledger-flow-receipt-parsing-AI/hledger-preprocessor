import csv
from typing import Dict, List, Union

from typeguard import typechecked

from hledger_preprocessor.config.AccountConfig import AccountConfig
from hledger_preprocessor.csv_parsing.csv_has_header import (
    has_header0,
)
from hledger_preprocessor.csv_transaction_parsing.parse_asset_transaction import (
    parse_asset_transaction,
)
from hledger_preprocessor.file_reading_and_writing import (
    assert_file_exists,
    convert_input_csv_encoding,
    detect_file_encoding,
)
from hledger_preprocessor.generics.GenericTransactionWithCsv import (
    GenericCsvTransaction,
)
from hledger_preprocessor.generics.parse_generic_tnx_with_csv import (
    parse_generic_bank_transaction,
)
from hledger_preprocessor.generics.Transaction import Transaction
from hledger_preprocessor.TransactionObjects import AccountTransaction


# account_config.get_abs_csv_filepath(dir_paths_config=config.dir_paths)
@typechecked
def load_csv_transactions_from_file_per_year(
    *,
    abs_csv_filepath: str,
    account_config: AccountConfig,
    csv_encoding: str,
) -> Dict[int, List[Transaction]]:
    if account_config.has_input_csv():
        transactions_per_year: Dict[int, List[Transaction]] = (
            csv_to_transactions(
                input_csv_filepath=abs_csv_filepath,
                csv_encoding=csv_encoding,
                account_config=account_config,
            )
        )
        return transactions_per_year
    else:
        return {}


@typechecked
def csv_to_transactions(
    input_csv_filepath: str,
    csv_encoding: str,
    account_config: AccountConfig,
) -> Dict[int, List["Transaction"]]:
    """
    Process transactions from a CSV file: convert encoding, parse, and sort by year.

    Args:
        input_csv_filepath (str): Path to the input CSV file
        csv_encoding (str): Target encoding format
        account_holder (str): Name of the account holder
        bank (str): Name of the bank
        account_type (str): Type of account

    Returns:
        Dict[int, List[Transaction]]: Transactions sorted by year
    """
    assert_file_exists(filepath=input_csv_filepath)

    convert_input_csv_encoding(
        input_csv_filepath=input_csv_filepath, output_encoding=csv_encoding
    )

    total_transactions: List[Transaction] = parse_encoded_input_csv(
        input_csv_filepath=input_csv_filepath,
        account_config=account_config,
    )

    transactions_per_year: Dict[int, List[Transaction]] = (
        sort_transactions_on_years(transactions=total_transactions)
    )

    return transactions_per_year


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
    input_csv_filepath: str,
    account_config: AccountConfig,
) -> List[Transaction]:
    updated_encoding = detect_file_encoding(filepath=input_csv_filepath)

    with open(
        input_csv_filepath,
        encoding=updated_encoding,
        errors="replace",
    ) as infile:
        reader = csv.reader(infile)
        rows = list(reader)

    transactions = process_transactions(
        rows=rows,
        input_csv_filepath=input_csv_filepath,
        account_config=account_config,
    )

    return transactions


@typechecked
def process_transactions(
    rows: List[List[str]],
    input_csv_filepath: str,
    account_config: AccountConfig,
) -> List[Transaction]:
    transactions: List[Union[GenericCsvTransaction, AccountTransaction]] = []

    all_indices_start_at: int
    if account_config.has_input_csv():

        if has_header0(csv_file_path=input_csv_filepath):

            all_indices_start_at: int = 1
        else:
            all_indices_start_at: int = 0
    else:
        all_indices_start_at: int = 1

    for index in range(all_indices_start_at, len(rows)):
        if account_config.has_input_csv():
            transaction: GenericCsvTransaction = parse_generic_bank_transaction(
                row=rows[index],
                nr_in_batch=index,
                account_config=account_config,
                csv_column_mapping=account_config.csv_column_mapping,
            )
            transactions.append(transaction)
        else:

            transaction: AccountTransaction = parse_asset_transaction(
                row=rows[index]
            )
            if transaction:
                transactions.append(transaction)
        index += 1
    return transactions


@typechecked
def get_years(*, transactions: List[Transaction]) -> List[int]:
    years: List[int] = [transaction.get_year() for transaction in transactions]
    return years
