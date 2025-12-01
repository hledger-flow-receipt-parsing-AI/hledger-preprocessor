import logging
from typing import Dict, List, Union

from hledger_preprocessor.config.AccountConfig import AccountConfig
from hledger_preprocessor.generics.Transaction import Transaction
from hledger_preprocessor.matching.ask_user_action import (
    ActionDataset,
    ActionValuePair,
    ReceiptMatchingAction,
)
from hledger_preprocessor.matching.linking.few_matches import handle_few_matches
from hledger_preprocessor.matching.linking.many_matches import (
    handle_many_matches,
)
from hledger_preprocessor.matching.linking.no_matches import handle_no_matches
from hledger_preprocessor.matching.linking.one_match import auto_link_receipt
from hledger_preprocessor.matching.manual_actions.inject_transaction_into_receipt import (
    inject_csv_transaction_to_receipt,
)
from hledger_preprocessor.TransactionObjects.Receipt import (
    Account,
    AccountTransaction,
    Receipt,
)

logger = logging.getLogger(__name__)
import logging
from typing import Dict, List

from typeguard import typechecked


@typechecked
def handle_receipt_item_transaction_to_csv_matches(
    *,
    transaction_matches: List[Transaction],
    # config: Config,
    csv_transactions_per_account: Dict[
        AccountConfig, Dict[int, List[Transaction]]
    ],
    actions_value: List[ActionValuePair],
    action_dataset: ActionDataset,
    # original_receipt_account_transaction: Optional[AccountTransaction] = None,
) -> None:

    receipt_account: Account = (
        action_dataset.search_receipt_account_transaction.account
    )
    if len(transaction_matches) == 1:
        found_csv_transaction: Transaction = transaction_matches[0]

        # Check if the receipt needs to be updated.
        updated_receipt: Union[None, Receipt] = (
            handle_alternate_currency_withdrawl(
                actions_value=actions_value,
                original_receipt_account_transaction=action_dataset.original_receipt_account_transaction,
                found_csv_transaction=found_csv_transaction,
                receipt=action_dataset.receipt,
            )
        )

        if updated_receipt:
            if action_dataset.original_receipt is None:
                action_dataset.original_receipt = action_dataset.receipt
            action_dataset.receipt = updated_receipt

        # handle_update_receipt(action_dataset=action_dataset)
        auto_link_receipt(
            action_dataset=action_dataset,
            found_csv_transaction=transaction_matches[0],
            original_receipt_account_transaction=action_dataset.search_receipt_account_transaction,
        )
    elif len(transaction_matches) == 0:
        handle_no_matches(
            csv_transactions_per_account=csv_transactions_per_account,
            actions_value=actions_value,
            action_dataset=action_dataset,
        )
    elif len(transaction_matches) < 15:
        handle_few_matches(
            original_receipt_account_transaction=action_dataset.search_receipt_account_transaction,
            transaction_matches=transaction_matches,
            receipt_account=receipt_account,
            csv_transactions_per_account=csv_transactions_per_account,
            actions_value=actions_value,
            action_dataset=action_dataset,
        )

    else:
        handle_many_matches(
            receipt,
            account,
            transactions_per_account,
            config,
        )


@typechecked
def handle_alternate_currency_withdrawl(
    *,
    actions_value: List[ActionValuePair],
    original_receipt_account_transaction: Union[None, AccountTransaction],
    found_csv_transaction: Transaction,
    receipt: Receipt,
) -> Union[None, Receipt]:
    count: int = sum(
        1
        for avp in actions_value
        if avp.action == ReceiptMatchingAction.ALTERNATE_CURRENCY_WITHDRAWL
    )
    if count > 1:
        raise ValueError(
            "More than one ALTERNATE_CURRENCY_WITHDRAWL action found"
        )
    elif count == 1:
        if original_receipt_account_transaction is None:
            raise ValueError(
                "If a foreign currency is withdrawn, then an original"
                " transaction (containing the bank csv equivalent"
                " (approximation) should be present.)"
            )
        # Inject the receipt foreign currency transactions.
        return inject_csv_transaction_to_receipt(
            original_receipt_account_transaction=original_receipt_account_transaction,
            found_csv_transaction=found_csv_transaction,
            receipt=receipt,
        )
