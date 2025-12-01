# TL;DR

To do your bookkeeping from scratch, copy and modify the [example_config.yaml](example_config.yaml) using follow these steps:

## A. Include .csv input files in account_configs in the config.yaml.

So download the transaction `.csv` files from your bank, store them, and store where you stored them in the above `config.csv`.

## B. Adding a start position (Optional)

You can include your financial starting position. For example your bank may/does/should not know whether you got a golden ring from your grandparents, yet it may have material value as well. You may have debts etc. So if you want a complete (private) overview of your full/absolute financial position, and not just the changes registered through your bank and/or receipts, you may want to add a starting position, using hledger journal files.

To understand how to create a starting position journal, see [B_using_hledger.md](B_using_hledger.md).

The start position is included in `start_journal_filepath` in the `config.yaml`

## C.0 Install requirements

```sh
conda env create --file environment.yml
snap install yq
# Install stack to install hledger-flow from:
# https://docs.haskellstack.org/en/stable/
# Install hledger-flow:

cd ~/finance/

cd hledger-flow
# https://github.com/apauley/hledger-flow/blob/master/CONTRIBUTING.org#build-the-project
# Add stack to path in ~/.bashrc:
export PATH="~/.local/bin:$PATH"

git clone git@github.com:a-t-0/hledger-flow.git
./bin/build-and-test
# Add hledger-flow to path (this is already done as stack is also stored there but maybe directions change.)
export PATH="~/.local/bin:$PATH"

# Install hledger
sudo apt install hledger

# Instal hledger-plot
cd ~/finance/
git clone git@github.com:a-t-0/hledger-plot.git
cd hledger-flot
rm -r build
python -m build
pip install -e .
```

## C. Configure start.sh

Set the `export ..` values in your `start.sh`. For example:

```sh
# Change this configuration to match your own setup.
export FINANCE_DIR="/home/$(whoami)/finance"
export WORKING_DIR="$FINANCE_DIR/finance_v8"
export START_JOURNAL_FILEPATH="$FINANCE_DIR/start_pos/2024_complete.journal"
export RECEIPT_IMAGES_DIR="$FINANCE_DIR/receipt_images"
export RECEIPT_LABELS_DIR="$FINANCE_DIR/receipt_labels"
export BANK_CONFIG_FILE="$FINANCE_DIR/banks_config.csv"
# End of configuration.
```

## D. Magic

Run:

```sh
chmod +x start.sh
./start.sh
```

And you will see your financial position, or get errors (see [troubleshooting](J_old_commands.md)).
