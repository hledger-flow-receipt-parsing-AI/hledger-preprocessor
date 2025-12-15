from copy import deepcopy
from decimal import Decimal
from pprint import pprint
from typing import List

from typeguard import typechecked

from hledger_preprocessor.generics.GenericTransactionWithCsv import (
    GenericCsvTransaction,
)
from hledger_preprocessor.generics.Transaction import Transaction
from hledger_preprocessor.receipt_transaction_matching.compare_transaction_to_receipt import (
    collect_non_csv_transactions,
)
from hledger_preprocessor.TransactionObjects.AccountTransaction import (
    AccountTransaction,
)
from hledger_preprocessor.TransactionObjects.Receipt import Receipt


@typechecked
def inject_csv_transaction_to_receipt(
    *,
    original_receipt_account_transaction: AccountTransaction,
    found_csv_transaction: Transaction,
    receipt: Receipt,
) -> Receipt:
    """
    Injects a bank transaction into a Receipt object, linking it to the provided bank details.
    Assumes the provided amount is already in the receipt's currency (e.g., pounds).

    Args:
        receipt: The Receipt object to inject the transaction into.
        bank_account_holder_name: The name of the account holder.
        bank_name: The name of the bank.
        bank_account_type: The type of bank account (e.g., 'checking', 'savings').
        amount: The amount paid in the receipt's currency (e.g., ~103 pounds).
        amount_returned: The amount returned in the receipt's currency (default 0.0).

    Returns:
        Receipt: A new Receipt object with the updated transaction details.

    Raises:
        ValueError: If the transaction details are invalid or do not match the receipt's total.
        TypeError: If the account type is invalid.
    """
    # Create a deep copy of the original receipt to avoid modifying it.
    new_receipt = deepcopy(receipt)

    # Create an Account object for the bank transaction.
    if float(
        Decimal(str(original_receipt_account_transaction.amount_out_account))
        - Decimal(str(original_receipt_account_transaction.change_returned))
        > 0
    ):

        # This assumes that the updated transaction contains the the original csv_bank account and the amount payed (and 0 change returned) in the currency of that original csv bank account.
        new_receipt: Receipt = (
            find_matching_receipt_transaction_and_inject_csv_transaction(
                receipt=new_receipt,
                original_receipt_account_transaction=original_receipt_account_transaction,
                found_csv_transaction=found_csv_transaction,
            )
        )
    else:
        raise NotImplementedError(
            "Do not yet know how to handle a foreign currency withdrawl that"
            " yielded money from the bank account for a receipt that only"
            " contained the foreign retrieved amount."
        )
    return new_receipt


@typechecked
def find_matching_receipt_transaction_and_inject_csv_transaction(
    *,
    receipt: Receipt,
    original_receipt_account_transaction: AccountTransaction,
    found_csv_transaction: Transaction,
) -> Receipt:
    if receipt_already_contains_csv_transaction(
        receipt=receipt, csv_transaction=found_csv_transaction
    ):
        raise SystemError(
            "Should not try to add transaction that is already added."
        )
    else:
        # Inject the csv_transaction into the receipt transaction.
        has_injected: bool = False
        all_account_transactions: List[AccountTransaction] = (
            collect_non_csv_transactions(receipt=receipt, verbose=False)
        )
        for receipt_account_transaction in all_account_transactions:
            if receipt_account_transaction.__eq__(
                original_receipt_account_transaction
            ):
                object.__setattr__(
                    receipt_account_transaction,
                    "original_transaction",
                    found_csv_transaction,
                )
                has_injected = True
        if not has_injected:
            pprint(receipt)
            print(
                f"original_receipt_account_transaction={original_receipt_account_transaction}"
            )
            print(f"found_csv_transaction={found_csv_transaction}")
            raise SystemError("Should have injected by now.")

        # Assert the csv_transaction has been injected into the receipt.
        # TODO: assert that the original csv transaction is found within receipt.

        if not receipt_already_contains_csv_transaction(
            receipt=receipt, csv_transaction=found_csv_transaction
        ):
            pprint(receipt)
            raise NotImplementedError(
                "The csv_transaction should have been found by now."
            )
    return receipt


@typechecked
def receipt_already_contains_csv_transaction(
    *, receipt: Receipt, csv_transaction: Transaction
) -> bool:
    # Collect account transactions in receipt.
    if not isinstance(csv_transaction, Transaction):
        raise TypeError(f"Unsupported csv transaction type:{csv_transaction}")
    receipt_transactions: List[AccountTransaction] = (
        collect_non_csv_transactions(receipt)
    )
    if not receipt_transactions:
        return False

    nr_of_matches: int = 0
    for receipt_transaction in receipt_transactions:
        if receipt_transaction.original_transaction:
            if not (
                isinstance(
                    receipt_transaction.original_transaction,
                    GenericCsvTransaction,
                )
                or isinstance(
                    receipt_transaction.original_transaction, AccountTransaction
                )
            ):
                raise TypeError(
                    "Found unexpected"
                    f" type:{receipt_transaction.original_transaction}"
                )
            # if isinstance(receipt_transaction.original_transaction, dict):
            #     csv_transaction_in_receipt: GenericCsvTransaction = (
            #         GenericCsvTransaction(
            #             **receipt_transaction.original_transaction
            #         )
            #     )
            if (
                # receipt_transaction.original_transaction.get_hash()
                receipt_transaction.original_transaction.get_hash()
                == csv_transaction.get_hash()
            ):
                nr_of_matches += 1
    if nr_of_matches == 1:
        return True
    elif nr_of_matches > 1:
        raise ValueError(
            "Found the same csv transaction more than once in single receipt."
        )
    elif nr_of_matches == 0:
        return False
    else:
        raise SystemError(
            "Should not be able to reach this state, perhas rad particles or"
            " debugging altered state mid computation."
        )
