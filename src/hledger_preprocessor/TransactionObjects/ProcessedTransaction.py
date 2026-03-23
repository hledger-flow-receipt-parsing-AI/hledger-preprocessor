import logging
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

logger = logging.getLogger(__name__)


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

            # Inject withdrawal metadata for multi-posting journal entries.
            wm = self.parent_receipt.withdrawal_metadata
            if wm is not None:
                src = wm.source_account_transaction
                data["withdrawal_source_account"] = (
                    f"{src.account.account_holder}:"
                    f"{src.account.bank}:{src.account.account_type}"
                )
                data["withdrawal_source_amount"] = str(
                    src.tendered_amount_out
                )
                data["withdrawal_source_currency"] = (
                    src.account.base_currency.value
                )
                data["withdrawal_atm_fee"] = str(wm.atm_operator_fee)
                if wm.withdrawn_amount is not None:
                    data["withdrawal_dest_amount"] = str(wm.withdrawn_amount)
                else:
                    data["withdrawal_dest_amount"] = ""
                if wm.exchange_rate is not None:
                    data["withdrawal_exchange_rate"] = str(wm.exchange_rate)
                else:
                    data["withdrawal_exchange_rate"] = ""
                data["withdrawal_bank_fx_fee"] = str(wm.bank_fx_fee)

                # Inject destination (wallet) account for bank-side
                # rules — needed so the bank CSV's withdrawal rule can
                # reference the wallet account.
                from hledger_preprocessor.TransactionObjects.AccountTransaction import (
                    AccountTransaction as AT,
                )
                from hledger_preprocessor.TransactionObjects.Receipt import (
                    Receipt as ReceiptCls,
                )

                dest_account_str = ""
                dest_change_returned = ""
                dest_currency = ""

                # Only extract dest account from real Receipt objects
                # (tests may pass mock objects without the full structure).
                if isinstance(self.parent_receipt, ReceiptCls):
                    from hledger_preprocessor.receipt_transaction_matching.compare_transaction_to_receipt import (
                        collect_non_csv_transactions,
                    )

                    for acct_txn in collect_non_csv_transactions(
                        self.parent_receipt
                    ):
                        if isinstance(acct_txn, AT):
                            acct = acct_txn.account
                            # The dest account is the one that is NOT
                            # the source bank account.
                            if not (
                                acct.account_holder
                                == src.account.account_holder
                                and acct.bank == src.account.bank
                                and acct.account_type
                                == src.account.account_type
                            ):
                                dest_account_str = (
                                    f"{acct.account_holder}:"
                                    f"{acct.bank}:{acct.account_type}"
                                )
                                dest_change_returned = str(
                                    acct_txn.change_returned
                                )
                                dest_currency = (
                                    acct.base_currency.value
                                )
                                break

                data["withdrawal_dest_account"] = dest_account_str
                data["withdrawal_change_returned"] = dest_change_returned
                data["withdrawal_dest_currency"] = dest_currency

                # US6: Balance validation for domestic withdrawals.
                # amount_debited == change_returned + atm_fee + bank_fee
                if not wm.is_foreign and dest_change_returned:
                    source_amt = round(src.tendered_amount_out, 2)
                    change_amt = round(float(dest_change_returned), 2)
                    atm_fee = round(wm.atm_operator_fee, 2)
                    bank_fee = round(wm.bank_fx_fee, 2)
                    expected = round(change_amt + atm_fee + bank_fee, 2)
                    if source_amt != expected:
                        logger.warning(
                            "Withdrawal balance mismatch for receipt %s: "
                            "source_amount=%.2f != change_returned(%.2f) "
                            "+ atm_fee(%.2f) + bank_fee(%.2f) = %.2f",
                            self.parent_receipt.raw_img_filepath,
                            source_amt,
                            change_amt,
                            atm_fee,
                            bank_fee,
                            expected,
                        )

        # data["ai_classifications"] = self.ai_classifications
        # data["logic_classifications"] = self.logic_classifications

        data.update(self.logic_classifications)
        data.update(self.ai_classifications)
        return data
