from datetime import datetime
from typing import Union

from hledger_preprocessor.config import AccountConfig
from hledger_preprocessor.config.Config import Config
from hledger_preprocessor.config.helper import get_account_config
from hledger_preprocessor.Currency import Currency
from hledger_preprocessor.generics.GenericTransactionWithCsv import (
    GenericCsvTransaction,
)
from hledger_preprocessor.TransactionObjects.AccountTransaction import (
    Account,
    AccountTransaction,
)


def initialize_account_transaction(
    *,
    config: Config,
    transaction: dict,
    account: Account,
    currency: Currency,
    the_date: datetime,
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

        if "original_transaction" in transaction.keys():
            transaction.pop("original_transaction")

        # TODO: assert account is equal to that of AccountConfig.
        if not isinstance(transaction["account"], Account):
            transaction["account"]["base_currency"] = Currency(
                transaction["account"]["base_currency"]
            )
            transaction["account"] = Account(
                **transaction["account"],
            )
        # if "change_returned" in transaction.keys():
        # if transaction["change_returned"] == 0:
        # transaction.pop("change_returned")
        return GenericCsvTransaction(**transaction)
    else:

        return AccountTransaction(
            the_date=the_date,
            account=account,
            # currency=currency,
            tendered_amount_out=transaction["tendered_amount_out"],
            change_returned=transaction["change_returned"],
            # original_transaction=original_transaction,
        )
