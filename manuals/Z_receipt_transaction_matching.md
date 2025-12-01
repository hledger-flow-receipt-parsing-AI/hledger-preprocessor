# Receipt Transaction Matching

The receipts can be matched to transactions using a matching algorithm. It uses the following steps:
First all transactions from all accounts are found.
Then per account, all transactions are taken.
Then all receipts are used.
Then for each receipt the receipt that has a transaction on the current account is evaluated.

This order is not logical, instead one should loop over all receipts, then per receipt find all the accounts that are involved with the receipt. If an account is not found, the user should be asked to create the account. (The account can be an asset like gold or BTC, or a bank account uniswap account etc).
A preliminary check should be done to indicate which accounts and/or asset categories are missing. The user should be instructed on where to add those.

Per receipt
for all accounts over accounts,
select_relevant_accounts.

get receipt transaction date, time and amount.
for relevant account in relevant_accounts:
find all yearly_transactions of that year of that account +- 5 days.
for each transaction in yearly_transactions
select the ones that match on exact amount +-amount margin (e.g. due to rounding)
if 1 match is found:
auto-link
elif 0 matches are found:
if month and day of receipt can be swapped:
retry with month and day of receipt swapped
elif:
Ask the user wants to:
\- check if the receipt is correct
\- check if the transactions of the relevant category are up to date (if the latest transaction data of that account is already included)
\- widen the yearly margin in days.
\- widen the transaction banking-delay margin
\- widen the amount margin
for this receipt and retry.
if more than 1 match is found, but less than 15:
load transactions and sort them based on a weighted closeness score.
if more than 15 are found:
Ask the user wants to:
\- check if the receipt is correct
\- check if the transactions of the relevant category are up to date (if the latest transaction data of that account is already included)
\- reduce the yearly margin in days.
\- reduce the transaction banking-delay margin
\- reduce the amount margin
for this receipt and retry.

## Weighted closeness score:

The weighted closeness score evaluates how closely a transaction matches a receipt based on date, time, and amount differences. It assigns weights to each factor to prioritize their importance, with lower scores indicating a better match. Date difference is weighted highest, followed by amount, then time.

```py
from datetime import datetime
import math

def weighted_closeness_score(
    receipt_date: datetime,
    receipt_amount: float,
    transaction_date: datetime,
    transaction_amount: float,
    date_weight: float = 0.5,
    amount_weight: float = 0.3,
    time_weight: float = 0.2
) -> float:
    """
    Compute the weighted closeness score between a receipt and a transaction.

    Args:
        receipt_date: The date and time of the receipt.
        receipt_amount: The amount on the receipt.
        transaction_date: The date and time of the transaction.
        transaction_amount: The amount of the transaction.
        date_weight: Weight for date difference (default: 0.5).
        amount_weight: Weight for amount difference (default: 0.3).
        time_weight: Weight for time difference (default: 0.2).

    Returns:
        A float representing the weighted closeness score (lower is better).
    """
    # Calculate date difference in days
    date_diff = abs((receipt_date.date() - transaction_date.date()).days)

    # Calculate time difference in hours (if applicable)
    time_diff = abs((receipt_date - transaction_date).total_seconds() / 3600)

    # Calculate amount difference as a percentage
    amount_diff = abs(receipt_amount - transaction_amount) / max(receipt_amount, 0.01)

    # Normalize differences (using a simple scaling factor to keep scores reasonable)
    normalized_date_diff = min(date_diff / 5.0, 1.0)  # Scale down date difference
    normalized_time_diff = min(time_diff / 24.0, 1.0)  # Scale down time difference
    normalized_amount_diff = min(amount_diff, 1.0)  # Cap amount difference

    # Compute weighted score
    score = (
        date_weight * normalized_date_diff +
        amount_weight * normalized_amount_diff +
        time_weight * normalized_time_diff
    )

    return score
```
