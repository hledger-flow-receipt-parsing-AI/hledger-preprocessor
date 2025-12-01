from pprint import pprint
from typing import Dict

from hledger_preprocessor.config import AccountConfig
from hledger_preprocessor.config.Config import Config
from hledger_preprocessor.config.helper import get_account_config
from hledger_preprocessor.Currency import Currency
from hledger_preprocessor.generics.GenericTransactionWithCsv import (
    GenericBankTransaction,
)
from hledger_preprocessor.TransactionObjects.AccountTransaction import (
    Account,
    AccountTransaction,
)


def initialize_account_transaction(
    *, config: Config, transaction: dict, account: Account, currency: Currency
) -> AccountTransaction:
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
        GenericBankTransaction(**transaction)

    if (
        "original_transaction" in transaction.keys()
        and transaction["original_transaction"] is not None
    ):
        from hledger_preprocessor.TransactionTypes.TriodosTransaction import (
            TriodosTransaction,
        )

        tnx_dict: Dict = transaction["original_transaction"]
        account: Account = Account(
            account_holder=tnx_dict["account_holder"],
            bank=tnx_dict["bank"],
            account_type=tnx_dict["account_type"],
            base_currency=Currency("EUR"),  # TODO: take from config.
        )

        pprint(tnx_dict)
        original_transaction: TriodosTransaction = TriodosTransaction(
            account=account,
            nr_in_batch=tnx_dict["nr_in_batch"],
            the_date=tnx_dict["the_date"],
            account0=tnx_dict["account0"],
            # amount0 = float(amount0.replace(',', '.')),
            amount_out_account=tnx_dict["amount0"],
            transaction_code=tnx_dict["transaction_code"],
            other_party_name=tnx_dict["other_party_name"],
            account1=tnx_dict["account1"],
            BIC=tnx_dict["BIC"],
            description=tnx_dict["description"],
            balance0=tnx_dict["balance0"],
        )
    else:
        original_transaction = None

    return AccountTransaction(
        account=account,
        currency=currency,
        amount_paid=transaction["amount_paid"],
        change_returned=transaction["change_returned"],
        original_transaction=original_transaction,
    )
