"""Random data generators for testing."""

import random
from datetime import datetime
from decimal import Decimal
from random import choices, randint
from string import ascii_lowercase
from typing import List

from typeguard import typechecked

from hledger_preprocessor.TransactionObjects.BuyWithPostingsTransaction import (
    BuyWithPostingsTransaction,
)
from hledger_preprocessor.TransactionObjects.Posting import (
    Posting,
    TransactionCode,
)


@typechecked
def generate_random_category(min_length: int = 3, max_length: int = 10) -> str:
    """Generate a random category string with lowercase letters and colons.

    Args:
        min_length: Minimum length of each category segment.
        max_length: Maximum length of each category segment.

    Returns:
        A random category string (e.g., "groceries:food:organic").

    Raises:
        ValueError: If the generated category is empty.
    """
    category_chars = ascii_lowercase + ":"

    # Start category with only ascii chars (no colons at start)
    random_category: str = "".join(
        choices(ascii_lowercase, k=randint(min_length, max_length))
    )

    # Add more characters including colons
    random_category = (
        f'{random_category}{"".join(choices(category_chars, k=randint(min_length, max_length)))}'
    )

    if random_category == "":
        raise ValueError("Generated category was empty.")

    return random_category


@typechecked
def diff_credit_larger_than_debit(
    *, debit_postings: List[Posting], credit_postings: List[Posting]
) -> Decimal:
    """Calculate the difference between credit and debit posting totals.

    Args:
        debit_postings: List of debit postings.
        credit_postings: List of credit postings.

    Returns:
        credit_sum - debit_sum (positive if credits exceed debits).
    """
    debit_sum: Decimal = Decimal(
        sum(posting.amount for posting in debit_postings)
    )
    credit_sum: Decimal = Decimal(
        sum(posting.amount for posting in credit_postings)
    )
    return credit_sum - debit_sum


@typechecked
def generate_random_transaction_with_n_postings(
    n: int,
) -> BuyWithPostingsTransaction:
    """Generate a random balanced transaction with n postings.

    Creates a transaction with random postings and automatically balances
    the debits and credits by adding a balancing posting if needed.

    Args:
        n: The number of postings to generate (before balancing).

    Returns:
        A balanced BuyWithPostingsTransaction with at least n postings.

    Raises:
        ValueError: If a posting has zero amount or balancing fails.
        TypeError: If an invalid posting type is encountered.
    """
    account_holder = "John Doe"
    bank = "Random Bank"
    account_type = "Checking"
    the_date = datetime.now()
    receipt_category = generate_random_category()

    credit_postings: List[Posting] = []
    debit_postings: List[Posting] = []

    for _ in range(n):
        category = generate_random_category()
        amount: Decimal = round(Decimal(random.uniform(1, 10000)), 10)

        if amount == 0:
            raise ValueError("Posting cannot have a value of 0.")

        posting_type = choices([TransactionCode.DEBIT, TransactionCode.CREDIT])[
            0
        ]

        posting = Posting(category, the_date, amount, posting_type)

        if posting_type == TransactionCode.DEBIT:
            debit_postings.append(posting)
        elif posting_type == TransactionCode.CREDIT:
            credit_postings.append(posting)
        else:
            raise TypeError(f"Unknown posting type: {posting_type}")

    # Balance the postings
    diff = diff_credit_larger_than_debit(
        credit_postings=credit_postings, debit_postings=debit_postings
    )

    if diff > 0:
        debit_postings.append(
            Posting(
                category="Debit balancer",
                the_date=the_date,
                amount=diff,
                posting_type=TransactionCode.DEBIT,
            )
        )
    elif diff < 0:
        credit_postings.append(
            Posting(
                category="Credit balancer",
                the_date=the_date,
                amount=-diff,
                posting_type=TransactionCode.CREDIT,
            )
        )

    # Verify balance
    final_diff = diff_credit_larger_than_debit(
        credit_postings=credit_postings, debit_postings=debit_postings
    )
    if final_diff != 0:
        raise ValueError(
            f"Failed to balance postings. Difference: {final_diff}"
        )

    return BuyWithPostingsTransaction(
        account_holder,
        bank,
        account_type,
        the_date,
        receipt_category,
        credit_postings,
        debit_postings,
    )
