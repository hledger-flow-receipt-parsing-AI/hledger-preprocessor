from typing import Protocol, Tuple

from hledger_preprocessor.TransactionObjects.Receipt import Receipt


class ReceiptImageToObjModel(Protocol):

    def image_path_to_receipt(
        self, receipt_filepath: str
    ) -> Tuple[str, Receipt]: ...
    def get_name(self) -> str: ...
