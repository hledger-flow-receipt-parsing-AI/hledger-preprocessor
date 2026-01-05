from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Dict, Optional, Union

from typeguard import typechecked

from hledger_preprocessor.config.AccountConfig import AccountConfig
from hledger_preprocessor.csv_parsing.get_hledger_dict import get_hledger_dict
from hledger_preprocessor.generics.GenericTransactionWithCsv import (
    GenericCsvTransaction,
)
from hledger_preprocessor.generics.Transaction import Transaction

# from hledger_preprocessor.triodos_logic import TriodosTransaction
if TYPE_CHECKING:
    from hledger_preprocessor.TransactionObjects.Receipt import Receipt


@typechecked
@dataclass(frozen=True, unsafe_hash=True)
class ProcessedTransaction:
    transaction: Transaction
    ai_classifications: Dict[str, str]
    logic_classifications: Dict[str, str]
    parent_receipt: Optional["Receipt"] = None

    # ai_classifications: Dict[str, str] = field(default_factory=dict)
    # logic_classifications: Dict[str, str] = field(default_factory=dict)

    def to_hledger_dict(
        self, account_config: Optional[AccountConfig] = None
    ) -> Dict[str, Union[int, float, str, datetime, None]]:

        if isinstance(self.transaction, GenericCsvTransaction):

            hledger_tnx_dict: Dict = get_hledger_dict(
                transaction=self.transaction, account_config=account_config
            )
        else:
            hledger_tnx_dict: Dict = get_hledger_dict(
                transaction=self.transaction, account_config=account_config
            )

        # This automatically calls the correct subclass implementation
        data = hledger_tnx_dict

        # Inject enrichment data into the dictionary
        if self.parent_receipt:
            data["receipt_link"] = self.parent_receipt.raw_img_filepath
        # data["ai_classifications"] = self.ai_classifications
        # data["logic_classifications"] = self.logic_classifications

        data.update(self.logic_classifications)
        data.update(self.ai_classifications)
        return data
