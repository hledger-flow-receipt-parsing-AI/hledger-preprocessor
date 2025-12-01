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
def generate_random_category(min_length=3, max_length=10):
    """Generates a random category string with only lowercase letters and colons."""
    category_chars = ascii_lowercase + ":"
    random_category: str = "".join(
        # Start category with only asci chars.
        choices(ascii_lowercase, k=randint(min_length, max_length))
    )
    random_category: str = (
        f'{random_category}{"".join(
        choices(category_chars, k=randint(min_length, max_length))
    )}'
    )
    if random_category == "":
        raise ValueError("Random_category was empty.")
    return random_category


@typechecked
def generate_random_transaction_with_n_postings(
    n: int,
) -> BuyWithPostingsTransaction:
    """
    Generates a random transaction (object) with `n` postings.

    Args:
        n: The number of postings in the transaction.

    Returns:
        A BuyWithPostingsTransaction object with random data.
    """

    # Generate random data for transaction fields
    account_holder = "John Doe"
    bank = "Random Bank"
    account_type = "Checking"
    the_date = datetime.now()
    receipt_category = generate_random_category()

    # Generate random postings
    credit_postings: List[Posting] = []
    debit_postings: List[Posting] = []

    for _ in range(n):
        # Generate random category, amount, and posting type.
        category = generate_random_category()
        # Random amount between 1 and 1000 with 2 decimals.
        amount: Decimal = round(Decimal(random.uniform(1, 10000)), 10)

        if amount == 0:
            raise ValueError("Posting cannot have a value of 0.")
        posting_type = choices([TransactionCode.DEBIT, TransactionCode.CREDIT])[
            0
        ]

        # Create and append the posting.
        posting = Posting(category, the_date, amount, posting_type)
        if posting_type == TransactionCode.DEBIT:
            debit_postings.append(posting)
        elif posting_type == TransactionCode.CREDIT:
            credit_postings.append(posting)
        else:
            raise TypeError("postinType not found.")

    # Balance the random postings.
    the_diff_credit_larger_than_debit: Decimal = diff_credit_larger_than_debit(
        credit_postings=credit_postings, debit_postings=debit_postings
    )
    if the_diff_credit_larger_than_debit > 0:
        debit_postings.append(
            Posting(
                category="Debit balancer",
                the_date=the_date,
                amount=the_diff_credit_larger_than_debit,
                posting_type=TransactionCode.DEBIT,
            )
        )
    elif the_diff_credit_larger_than_debit < 0:
        credit_postings.append(
            Posting(
                category="Credit balancer",
                the_date=the_date,
                amount=-the_diff_credit_larger_than_debit,
                posting_type=TransactionCode.CREDIT,
            )
        )
    if (
        diff_credit_larger_than_debit(
            credit_postings=credit_postings, debit_postings=debit_postings
        )
        != 0
    ):
        raise ValueError("Did not balance postings.")

    # Return the balanced generated transaction object with at least 2 postings.
    return BuyWithPostingsTransaction(
        account_holder,
        bank,
        account_type,
        the_date,
        receipt_category,
        credit_postings,
        debit_postings,
    )


@typechecked
def diff_credit_larger_than_debit(
    *, debit_postings: List[Posting], credit_postings: List[Posting]
) -> Decimal:
    debit_sum: Decimal = Decimal(
        sum(list(map(lambda posting: posting.amount, debit_postings)))
    )
    credit_sum: Decimal = Decimal(
        sum(list(map(lambda posting: posting.amount, credit_postings)))
    )
    return credit_sum - debit_sum
