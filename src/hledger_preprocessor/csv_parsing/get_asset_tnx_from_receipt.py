from typing import List, Union
from xml.dom import NotFoundErr

from typeguard import typechecked

from hledger_preprocessor.generics.GenericTransactionWithCsv import (
    GenericCsvTransaction,
)
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
        if possible_txn == some_txn:
            return True
    return False


# @typechecked
# def receipts_contain_asset_txn(*,
#                                receipts:List[Receipt],
#                                some_txn:AccountTransaction,
# )-> bool:
#     for receipt in receipts:
#         if receipt.the_date == some_txn.the_date:
#             if receipt_contains_asset_txn(receipt=receipt,some_txn=some_txn):
#                 return True
#     return False


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
    if len(matching_receipts) != 1:
        for i, matching_receipt in enumerate(matching_receipts):
            print(f"\n\n, i={i}")
            matching_receipt.pretty_print_receipt_without_config()
        raise NotFoundErr(
            f"Did not find exactly 1 matching receipt for txn:{some_txn},"
            f" found:{len(matching_receipts)}."
        )
