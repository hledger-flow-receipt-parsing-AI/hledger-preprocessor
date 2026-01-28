# Hledger .csv bank statement preprocessor for hledger-flow

[![Python 3.12][python_badge]](https://www.python.org/downloads/release/python-3120/)
[![License: AGPL v3][agpl3_badge]](https://www.gnu.org/licenses/agpl-3.0)
[![Code Style: Black][black_badge]](https://github.com/ambv/black)

This pip package is called by the
[modified hledger-flow repository](https://github.com/a-t-0/hledger-flow)
to pre-processes and categorise bank `.csv` files and receipts so that
`hledger-flow` can convert them into `hledger` journals.

\<TODO: insert randomized hledger plot with treemap>
\<TODO: insert randomized hledger plot with sankey>

## Demos (auto-generated from integration tests)

### Quick Start: 5-Step Workflow

**Step 1a: Configure your accounts**

Set up your bank accounts and wallets in `config.yaml`:

https://github.com/user-attachments/assets/PLACEHOLDER_1A_SETUP_CONFIG

**Step 1b: Define your categories**

Add spending categories to `categories.yaml`:

https://github.com/user-attachments/assets/PLACEHOLDER_1B_ADD_CATEGORY

**Step 2a: Rotate & Crop your receipts**

Use the CLI to rotate and crop your receipts (if necessary), to increase their zoomed readability and reduce noise.

https://github.com/user-attachments/assets/PLACEHOLDER_2A_CROP_RECEIPT

**Step 2b: Label your receipts**

Use the TUI to label receipt images with date, shop, amount, and payment method:

https://github.com/user-attachments/assets/PLACEHOLDER_2B_LABEL_RECEIPT

**Step 3: Match receipts to bank transactions**

Algorithmically/semi-automated linking of receipts to your bank/exchange CSV transactions (prevents *duplicate double-entry bookkeeping postings*):

https://github.com/user-attachments/assets/PLACEHOLDER_3_MATCH_RECEIPT

**Step 4: Run the pipeline**

Run `./start.sh` to generate journals and plots:

https://github.com/user-attachments/assets/PLACEHOLDER_4_RUN_PIPELINE

______________________________________________________________________

### Step 5: Visualize Your Finances

Use `hledger_plot` to create interactive Sankey diagrams and Treemap plots:

https://github.com/user-attachments/assets/PLACEHOLDER_5_SHOW_PLOTS

______________________________________________________________________

### Additional Features

- Include performance metrics of various self-hosted AIs:

\<TODO: add performance metrics various ai modules>

- AI for: bank `.csv` transaction-> categorisation (e.g. groceries:wholefoods, repairs:bike etc.)

\<TODO: add gif>

- AI for: receipt image -> structured text (e.g. a json/dictionary with the time, shop, bought items, total, taxes etc.)

\<TODO: add gif>

- AI for: receipt image -> categorisation (e.g. groceries, repairs etc.)

\<TODO: add gif>

## Getting Started

This is a HELPER-MODULE for `hledger-flow`.

To get started with this repo, see [TL;DR.md](TL;DR.md)

For troubleshooting or more understanding per module/component of your bookkeeping setup, see:

- [manuals/A_dev_instructions.md](manuals/A_dev_instructions.md).
- [manuals/B_using_hledger.md](manuals/B_using_hledger.md).
- [manuals/C_installing_hledger-flow.md](manuals/C_installing_hledger-flow.md).
- [manuals/D_using_hledger-flow.md](manuals/D_using_hledger-flow.md).
- [manuals/D_hledger_preprocessor.md](manuals/C_using_hledger.md).
- [manuals/J_TLDR.md](manuals/J_TLDR.md).

## Terminology

- A **journal** is a list of transactions, e.g: the icecream you bought on your way
  up to Mount Everest, and the salt you bought whilst swimming in the ocean etc.
- A **posting** is a single transaction in a journal.
- **Credit** is for currency going out of an account.
- **Debit** is for currency going into an account.
- **tendered_amount_out** if you pay 50,- (cash) and get 13.24 change back,
  `tendered_amount_out=50,-` going out of the account, with a
  `net_amount_out=tendered_amount_out-change_returned=50-13.24=46.76`.

## Introduction

I used to think that book keeping was an automated process. I did not think
about why people did bookkeeping, I thought it was just good habits/required.
However, (double-entry) bookkeeping is (currently) manual labour, as it
requires:

- A. Making a financial planning, of what you want to earn, spend and save.
- B. Tracking where your money went.
- C Checking how your actual income, expenses and savings compare to financial
  planning.
- D. Updating your habits and choices based on the/any difference, and re-starting
  the cycle.

For many people step A and B are already challenging do do consistently. I
expect steps C. and D. to be even harder.

## Context

In double-entry bookkeeping, transactions need to be classified into
categories, e.g. groceries, rent, income etc.

## Functionality

This preprocessing repo aims to support automatically parsing bank statements
and receipt images into information that hledger-flow can convert into
journals/postings.

### AI models

I prefer deterministic logic over AI models. Users can choose to use 3
different `SELF-HOSTED` AI models in this module:

- AI for: bank `.csv` transaction-> categorisation (e.g. groceries:wholefoods, repairs:bike etc.)
- AI for: receipt image -> structured text (e.g. a dictionary with the time, shop, bought items, total, taxes etc.)
- AI for: receipt image -> categorisation (e.g. groceries, repairs etc.)
  Users should always be able to choose to manually use their own logic instead
  of an AI.

### Bank statements

Bank statements like `.csv` files can relatively easily be categorised using
logic. For example, if the transaction is done at a groceries shop, you can
easily categorise the whole transaction as "groceries". However, that still
requires manual labour, so the user can also choose to use AI based transaction
classifications.

- Pure logic based transaction classification (preferred).
- AI-based auto-transaction classification.

Currently the bank `.csv` statement transaction AI classifiers are not that
good, I hope to build an open source dataset using the categorisation logic and
transactions to train/finetune categorisation models. I do not yet have a
pipeline to build that dataset.

### (Automated) Receipt Labelling

Receipts require more labour as they are to be read and converted into
digital format to parse them and convert them into `hledger` journals/postings.
So different AI models are used to automatically convert receipt images into
JSON `Receipt` objects. Then these `Receipt` objects are converted into
`Transaction` objects that can be converted into hledger journals/postings.

The receipts are first converted into receipt objects to store the receipt data
as completely as possible, such that the receipt object database can be used to
finetune/train the receipt-image->structured text AI models. However `hledger`
only needs specific data for its transactions, hence the `Receipt` object is
then converted into a `Transaction` object.

The receipt objects are not yet categorised automatically using the above AI.
\<TODO: insert example receipt image>
\<TODO: insert receipt CLI demo>

### Receipt transaction matching

Some receipts, e.g. those paid by bank card, will match the transactions in a
bank `.csv` statement. Some matching algorithm is proposed to auto-generate the
labels for the `receipt image -> structured text` database. For example:
if the receipt has a timestamp of 2025-01-29T21:55:95 and a bank account that
ends in `XXYY1342`, one can match it to the transaction of that time. A
matching algorithm has been implemented to automate the receipt matching to
`.csv` transactions and a CLI is built to resolve mismatches, e.g. in foreign
currency exchanges with withdrawl fees, as quick as possible. The match/link
is stored in both the transaction and the receipt.

\<TODO: insert matching algorithm CLI demo>

<!-- Un-wrapped URL's below (Mostly for Badges) -->

[agpl3_badge]: https://img.shields.io/badge/License-AGPL_v3-blue.svg
[black_badge]: https://img.shields.io/badge/code%20style-black-000000.svg
[python_badge]: https://img.shields.io/badge/python-3.6-blue.svg
