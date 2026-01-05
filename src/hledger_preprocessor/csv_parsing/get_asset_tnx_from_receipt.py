from pprint import pprint
from typing import List, Union
from xml.dom import NotFoundErr

from typeguard import typechecked

from hledger_preprocessor.generics.GenericTransactionWithCsv import (
    GenericCsvTransaction,
)
from hledger_preprocessor.generics.Transaction import Transaction
from hledger_preprocessor.TransactionObjects.AccountTransaction import (
    AccountTransaction,
)
from hledger_preprocessor.TransactionObjects.Receipt import Receipt


@typechecked
def receipt_contains_asset_txn(
    *,
    receipt: Receipt,
    some_txn: AccountTransaction,
) -> bool:

    possible_txns: List[Union[AccountTransaction, GenericCsvTransaction]] = (
        receipt.get_both_item_types()
    )
    for possible_txn in possible_txns:
        if Transaction.get_hash(possible_txn) == Transaction.get_hash(some_txn):

            return True
    return False


@typechecked
def get_receipt_that_contain_asset_txn(
    *,
    receipts: List[Receipt],
    some_txn: AccountTransaction,
) -> Receipt:
    assert_asset_txn_matches_one_receipt(receipts=receipts, some_txn=some_txn)

    matching_receipts: List[Receipt] = get_receipts_that_contain_asset_txn(
        receipts=receipts, some_txn=some_txn
    )
    return matching_receipts[0]


@typechecked
def assert_asset_txn_matches_one_receipt(
    *,
    receipts: List[Receipt],
    some_txn: AccountTransaction,
) -> None:

    matching_receipts: List[Receipt] = get_receipts_that_contain_asset_txn(
        receipts=receipts, some_txn=some_txn
    )
    # if len(matching_receipts) == 0:
    #     raise ValueError("Did not find any matching receipts.")
    if len(matching_receipts) != 1:
        for i, matching_receipt in enumerate(matching_receipts):
            print(f"\n\n, i={i}")
            matching_receipt.pretty_print_receipt_without_config()
        pprint(some_txn)
        raise NotFoundErr(
            "Did not find exactly 1 matching receipt for above txn:"
            f" found:{len(matching_receipts)} with:{matching_receipts}."
        )


@typechecked
def get_receipts_that_contain_asset_txn(
    *,
    receipts: List[Receipt],
    some_txn: AccountTransaction,
) -> List[Receipt]:
    matching_receipts: List[Receipt] = []

    for receipt in receipts:

        if receipt.the_date == some_txn.the_date:
            if receipt_contains_asset_txn(receipt=receipt, some_txn=some_txn):
                matching_receipts.append(receipt)

    return matching_receipts
