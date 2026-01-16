Hi Claude,

## Compiling

go into this directory, activate conda with:

```
conda activate hledger_preprocessor
```

There are several run commands. ./start.sh runs it all from start to finish, and that ends in a plot that can be seen from the browser at localhost:8050
./start.sh

## Config

look at the example config and load_config.py to see how that works, everyting should be recreated the same if run ./start.sh from the same csv input(s).

You can check that output to determine if your changes still allow succesfull compilation/running.

## Readmes

Some of the readmes contain outdated information. We will cleanup later.

## Context

This is the python module that orchestrates bookkeeping data preprocessing and labelling, along with a TUI to allow users to quickly label receipts.

## Requests

- Be consise and accurate in the text you write.

## testing:

The current testing command is:

```sh
clear && python -m pytest -k test_cli1 -W ignore
```
