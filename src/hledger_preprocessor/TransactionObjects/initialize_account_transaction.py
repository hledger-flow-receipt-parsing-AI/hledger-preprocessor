from datetime import datetime
from typing import Union

from hledger_preprocessor.config import AccountConfig
from hledger_preprocessor.config.Config import Config
from hledger_preprocessor.config.helper import get_account_config
from hledger_preprocessor.csv_parsing.helper import read_date
from hledger_preprocessor.Currency import Currency
from hledger_preprocessor.generics.GenericTransactionWithCsv import (
    GenericCsvTransaction,
)
from hledger_preprocessor.TransactionObjects.AccountTransaction import (
    Account,
    AccountTransaction,
)
from hledger_preprocessor.TransactionObjects.Posting import TransactionCode


def initialize_account_transaction(
    *,
    config: Config,
    transaction: dict,
    account: Account,
    currency: Currency,
    the_date: datetime,
    recursion_depth: int,
) -> Union[AccountTransaction, GenericCsvTransaction]:
    """
    Initialize an AccountTransaction with an optional TriodosTransaction.

    Args:
        transaction: Dictionary containing transaction data
        account: Account object
        currency: Currency enum

    Returns:
        AccountTransaction object

    Raises:
        ValueError: If multiple transaction types are supported or initialization fails
    """
    supported_types = ["TriodosTransaction"]

    if len(supported_types) > 1:
        raise ValueError(
            "Multiple transaction types are not supported. Only one type should"
            " be specified."
        )

    account_config: AccountConfig = get_account_config(
        config=config, account=account
    )

    if account_config.has_input_csv():

        if "currency" in transaction.keys():
            transaction.pop("currency")

        # Extract the date of the transaction — safely
        if "the_date" in transaction:
            pass  # already good
        elif (
            "original_transaction" in transaction
            and transaction["original_transaction"] is not None
            and "the_date" in transaction["original_transaction"]
        ):
            transaction["the_date"] = transaction["original_transaction"][
                "the_date"
            ]

        else:
            transaction["the_date"] = the_date
        if isinstance(transaction["the_date"], str):
            transaction["the_date"] = read_date(
                the_date_str=transaction["the_date"]
            )

        if "original_transaction" in transaction.keys():
            if recursion_depth < 1:
                transaction["original_transaction"] = (
                    initialize_account_transaction(
                        config=config,
                        transaction=transaction,
                        account=account,
                        currency=currency,
                        the_date=the_date,
                        recursion_depth=1,
                    )
                )
            else:
                transaction.pop("original_transaction")

        # TODO: assert account is equal to that of AccountConfig.
        if not isinstance(transaction["account"], Account):
            transaction["account"]["base_currency"] = Currency(
                transaction["account"]["base_currency"]
            )
            transaction["account"] = Account(
                **transaction["account"],
            )
        if (
            "transaction_code" in transaction.keys()
            and transaction["transaction_code"]
            and not isinstance(transaction["transaction_code"], TransactionCode)
        ):

            transaction["transaction_code"] = TransactionCode(
                transaction["transaction_code"]
            )
        return GenericCsvTransaction(**transaction)
    else:

        transaction["the_date"] = the_date
        transaction["account"] = account
        if "currency" in transaction.keys():
            transaction.pop("currency")

        if "original_transaction" in transaction.keys():
            if recursion_depth < 1:
                transaction["original_transaction"] = (
                    initialize_account_transaction(
                        config=config,
                        transaction=transaction,
                        account=account,
                        currency=currency,
                        the_date=the_date,
                        recursion_depth=1,
                    )
                )
            else:
                transaction.pop("original_transaction")
        account_txn: AccountTransaction = AccountTransaction(**transaction)

        return account_txn
