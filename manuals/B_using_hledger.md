# B. How to get started with hledger

This page explains the most automated bookkeepping setup with `hledger`. For
double-entry-accounting explanation see
[Bookkeeping_explained.md](Bookkeeping_explained.md).

You start your financial bookkeeping situation by manually creating a
`.journal` that contains all your assets and debts, in essence your
"net worth". From there-on out you start keeping track of your financial
situation over time.

## B.1. TL;DR Old manual start with hledger

1: Create a starter journal

```sh
mkdir -p ~/finance
cat > ~/finance/journal.ledger << EOF
; Example hledger journal
; This file tracks financial transactions.

2024-11-01 Income
    Assets:Bank:Checking     $1000.00
    Income:Salary

2024-11-02 Expenses
    Expenses:Food:Groceries   $150.00
    Assets:Bank:Checking
EOF
```

2. Or import multiple hledger files with a `main.journal` file that includes
   other files like:

```
include 2024.journal
include 2024_salads.journal
```

3. And then ensure your `~/.bashrc` file contains the line:

```sh
export LEDGER_FILE=~/finance/main.journal
```

4. Reload .bashrc to apply changes

```sh
source ~/.bashrc
```

## B.2. hledger CLI usage

This section explains how to use the `hledger` tool.

### B.2.1 Showing the balance in a single currency:

```sh
hledger bal -X EUR
```

outputs the total amount you have (-liabilites), in Euros (even if you added
BTC etc!).

### B.2.2 Showing assets

You can also show how much you have in possession without the liabilites with:

```sh
hledger bal -X EUR assets
```

### B.2.3 Forecasting

```sh
clear && hledger balance -M -A -b 2024-05 cur:Eur --forecast -T -X EUR
```

This shows how much each account changes/consumes every month, along with the
end balance of that account at the end of the forecasting period.

### B.2.4 Excluding equity from overview

```sh
clear && hledger balance -M -A -b 2024-05 -e 2025-03 --forecast -T assets expenses liabilities -X EUR
```

or:

```sh
clear && hledger balance -M -A -b 2024-05 -e 2025-03 --forecast -T -X EUR
```

### B.2.5 CLI Syntax

- `cur:Eur` only include transactions that are in Euros.
- `-X EUR` convert everything, e.g. gold to its worth in Euros.
- `balance` shows numbers (can be raw balance, or some changes over time dpeneding on arguments.)
- `-M` Monthly give the numbers per month.
- `-A` Average give the average numbers (per unit of time).
- `-b` Begin as of that date with the balance report.
- `-T` Total, display the total (end balance (as forecasted)).
- `--forecast` Give the forecast if the expenses are as you budgetted.

### B.2.6 Journal syntax

You can make a budget (expected transaction), by creating a periodic
transaction, however, the idea is that you then still add the actual
transaction when it occurs.
