# How to get started with pip package hledger_preprocessor

Assumes you looked at:

- [manuals/A_dev_instructions.md](manuals/A_dev_instructions.md).
- [manuals/B_using_hledger.md](manuals/B_using_hledger.md).
- [manuals/C_installing_hledger-flow.md](manuals/C_installing_hledger-flow.md).
- [manuals/D_using_hledger-flow.md](manuals/D_using_hledger-flow.md).
- [manuals/C_using_hledger.md](manuals/C_using_hledger.md).

This page explains the most automated bookkeepping setup with `hledger`. For
double-entry-accounting explanation see
[Bookkeeping_explained.md](Bookkeeping_explained.md).

You start your financial bookkeeping situation by manually creating a
`.journal` that contains all your assets and debts, in essence your
"net worth". From there-on out you start keeping track of your financial
situation over time.

## Structure

At its base it this bookkeeping software uses:
-`hledger` (Haskell alternative to beancount), which use plain-text accounting
files at their base.

- (a modded) `hledger-flow` as an opinionated way to structure your accounting files.

- `hledger-preprocessor` a Python pip package that does the pre-processing of
  your financial data. \`hledger-preprocessor has 2 main functionalities:

- Parsing and categorising `.csv` bank statements into the format of hledger
  postings/journals. It uses as little AI as possible for this, mainly you
  do the work yourself based on simple logic statements.

- Automatically converting receipt images into
  categorised hledger postings/journals, (using a finetuned model of the
  [Donut](https://github.com/clovaai/donut/issues/65) AI)).

- `hledger-plot` a Python pip package that visualises both your financial
  position and changes over time/per time-period, based on the `hledger-flow`
  structure and plain text journal/posting categorisations.
