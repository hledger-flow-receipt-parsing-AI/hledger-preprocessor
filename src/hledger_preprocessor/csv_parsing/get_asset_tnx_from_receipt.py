import logging
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

logger = logging.getLogger(__name__)


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
    matching_receipts: List[Receipt] = get_receipts_that_contain_asset_txn(
        receipts=receipts, some_txn=some_txn
    )

    if len(matching_receipts) == 0:
        pprint(some_txn)
        raise NotFoundErr(
            "Did not find any matching receipt for above txn."
        )

    if len(matching_receipts) > 1:
        # Multiple receipt photos of the same purchase were labelled
        # separately (violates US-X.6).  Warn and use the first one.
        img_paths = [r.raw_img_filepath for r in matching_receipts]
        logger.warning(
            "Found %d duplicate receipts for the same transaction "
            "(date=%s, amount=%s).  Using the first and ignoring the "
            "rest.  Duplicate images: %s",
            len(matching_receipts),
            some_txn.the_date,
            some_txn.tendered_amount_out,
            img_paths,
        )
        print(
            f"WARNING: {len(matching_receipts)} duplicate receipt labels "
            f"found for transaction on {some_txn.the_date} "
            f"amount={some_txn.tendered_amount_out}.  "
            f"Using: {img_paths[0]}"
        )

    return matching_receipts[0]


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
