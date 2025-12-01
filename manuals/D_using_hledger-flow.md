# D Using hledger-flow import

Assumes you looked at:

- [manuals/B_using_hledger.md](manuals/B_using_hledger.md).
- [manuals/B_installing_hledger.md](manuals/B_installing_hledger.md).

## D.1 Requirements

- Some `bank_statements.csv` file you downloaded from your bank.
- Some directory, e.g. `~/finance`, in which you will do your double-entry bookkeeping.
- pip package `hledger_preprocessor` works, is available in your (conda) CLI, and running it with `hledger_preprocessor --help` outputs:

```sh
usage: hledger_preprocessor [-h] -a ACCOUNT_HOLDER -b BANK -t ACCOUNT_TYPE [-n] [-c CSV_FILEPATH] [-i INPUT_FILE] [-g] -s START_PATH [-p PRE_PROCESSED_OUTPUT_DIR]

Convert Triodos Bank CSV to custom format.
...
```

- Haskell package `hledger-flow` works, is available in your (conda) CLI and running it with `hledger-flow --version` outputs:

```sh
hledger-flow 0.15.0 linux x86_64 ghc 9.4 0ba2e3132217b27addedae6a579d01b0cad61a21
```

## D.2 First run, creating the hledger-flow double-entry opinionated file structure

To create the new bookkeeping directory, use
Run:

```sh
mkdir -p ~/finance # Or any other dir, just use it consistently.
hledger_preprocessor --new --start-path ~/finance --csv-filepath ~/bank_statements.csv --account-holder account_holder --bank bank_name --account-type account_type
```

## D.3 Using hledger-flow import

After creating the bookkeeping folder structure in
[## D.1](manuals/D_using_hledger-flow.md##C.1), run `hledger-flow import` with:

```sh
cd ~/finance
hledger-flow import
```

## D.4 Troubleshooting

Then get the `hledger-preprocessor` command using:

```sh
cat preprocess_output.log
```

which contains something like:

```
hledger_preprocessor --csv-filepath ~/finance/import/swag/some_bank/some_type/1-in/2024/original.csv --start-path /home/a/finance/retry --account-holder swag --bank some_bank --account-type some_type --pre-processed-output-dir=2-preprocessed
```

## D.5 Don't look at

[this](https://github.com/apauley/hledger-flow-example/tree/master/import/gawie/bogart/cheque)
structure.
