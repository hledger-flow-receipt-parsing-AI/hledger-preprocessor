Hi Claude,

## Compiling

go into this directory, activate conda with:

```sh
conda activate hledger_preprocessor
```

There are several run commands. ./start.sh runs it all from start to finish, and that ends in a plot that can be seen from the browser at localhost:8050

## Config

look at the example config and load_config.py to see how that works, everyting should be recreated the same if run ./start.sh from the same csv input(s).

You can check that output to determine if your changes still allow succesfull compilation/running.

## Readmes

Some of the manuals/\*.md files contain outdated information. We will cleanup later.

## Context

This is the python module that orchestrates bookkeeping data preprocessing and labelling, along with a TUI to allow users to quickly label receipts.

## Requests

- Be consise and accurate in the text you write.

## testing:

Look at manuals/TESTING.md and test/e2e/test_gif_generation.py as examples of the test structure to follow.

```sh
conda activate hledger_preprocessor
python -m pytest
```
## Developing

Always check if your changes work.
Never just look at whether the tests passes, always also check whether the cli output does not contain any errors.

## Test Environment

Use `run_start_sh_test.py` in the project root to create a test environment at `~/finance_test` with sample data.
Then that script outputs how to run the ./start.sh code like:
NEXT STEP - Run start.sh with the config file:
------------------------------------------------------------
  ./start.sh --config /home/a/finance_test/config.yaml

