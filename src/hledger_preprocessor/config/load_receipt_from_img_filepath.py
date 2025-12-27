from typing import List

from typeguard import typechecked

from hledger_preprocessor.TransactionObjects.Receipt import Receipt


@typechecked
def load_receipt_from_img_filepath(
    *,
    raw_img_filepath: str,
    labelled_receipts: List[Receipt],
) -> Receipt:
    desired_receipts: List[Receipt] = []
    for receipt in labelled_receipts:
        if receipt.raw_img_filepath == raw_img_filepath:
            desired_receipts.append(receipt)
    if len(desired_receipts) == 1:
        return desired_receipts[0]

    raise LookupError(
        f"Expected only one receipt for:{raw_img_filepath},"
        f" found:{desired_receipts}"
    )
