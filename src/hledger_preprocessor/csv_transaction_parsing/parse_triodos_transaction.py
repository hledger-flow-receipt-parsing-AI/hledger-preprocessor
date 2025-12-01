"""Contains the logic for preprocessing Triodos .csv files to prepare them for
hledger."""

from datetime import datetime
from typing import List

from typeguard import typechecked

from hledger_preprocessor.Currency import Currency
from hledger_preprocessor.date_extractor import (
    get_date_from_bank_date_or_shop_date_description,
)
from hledger_preprocessor.TransactionObjects.Account import Account
from hledger_preprocessor.TransactionObjects.Posting import (
    TransactionCode,
)

# from hledger_preprocessor.TransactionTypes.TriodosTransaction import TriodosTransaction
from hledger_preprocessor.TransactionTypes.TriodosTransaction import (
    TriodosTransaction,
)


@typechecked
def parse_triodos_transaction(
    row: List[str],
    nr_in_batch: int,
    account_holder: str,
    bank: str,
    account_type: str,
) -> TriodosTransaction:

    # Split the row up into separate variables.
    (
        date_string,
        account0,
        amount0,
        transaction_code,
        other_party_name,
        account1,
        BIC,
        description,
        balance0,
    ) = row

    best_date: datetime = get_date_from_bank_date_or_shop_date_description(
        bank_date_str=date_string, description=description
    )
    account: Account = Account(
        account_holder=account_holder,
        bank=bank,
        account_type=account_type,
        base_currency=Currency("EUR"),  # TODO: take from config.
    )
    return TriodosTransaction(
        account=account,
        nr_in_batch=nr_in_batch,
        the_date=best_date,
        account0=account0,
        # amount0 = float(amount0.replace(',', '.')),
        amount_out_account=float(amount0.replace(".", "").replace(",", ".")),
        transaction_code=TransactionCode.normalize_transaction_code(
            transaction_code=transaction_code
        ),
        other_party_name=other_party_name,
        account1=account1,
        BIC=BIC,
        description=description,
        # balance0 = float(balance0.replace(',', '.'))
        balance0=float(balance0.replace(".", "").replace(",", ".")),
    )
