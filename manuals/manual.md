# hledger-preprocessor Manual

## Overview

This project automates personal bookkeeping using plain-text accounting. It
combines:

- **hledger** — Haskell-based plain-text accounting tool
- **hledger-flow** — opinionated directory structure for hledger files (custom fork)
- **hledger_preprocessor** — Python pip package that preprocesses bank CSVs, receipt
  images, and asset data into hledger journals
- **hledger_plot** — Python pip package that visualises financial data

The workflow: you provide a `config.yaml`, bank CSV exports, and optionally
receipt images. `start.sh` orchestrates everything — preprocessing, hledger-flow
import, and plotting.

---

## A. Quick Start

### A.1 Install prerequisites

```sh
conda env create --file environment.yml
conda activate hledger_preprocessor
pip install -e .
sudo snap install yq          # YAML parser used by start.sh
sudo apt install hledger       # plain-text accounting CLI
```

Install the custom hledger-flow fork:

```sh
# Install Haskell stack
curl -sSL https://get.haskellstack.org/ | sh
sudo apt-get install libgmp-dev

# Clone and build the fork
git clone git@github.com:a-t-0/hledger-flow.git
cd hledger-flow
chmod +x bin/build-and-test
./bin/build-and-test

# Add to path (if not already)
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc

# Verify
hledger-flow --version
```

### A.2 Configure

Copy and edit the example config:

```sh
cp example_config.yaml ~/finance/config.yaml
```

The config has these sections:

- **account_configs** — one entry per bank account / asset wallet, specifying
  the CSV file, currency, account holder, bank name, account type, and column
  mapping
- **dir_paths** — all relative to `root_finance_path`: working directory,
  receipt directories, asset CSVs, plot output
- **file_names** — start journal, root journal, categories file, receipt image
  naming conventions
- **categorisation** — `quick: true/false`
- **csv_encoding** — e.g. `utf-8`
- **matching_algo** — controls how receipts are matched to bank transactions
  (date window, amount range, month/day swap)

### A.3 Run

```sh
./start.sh --config ~/finance/config.yaml
```

This will:

1. Parse the config and validate prerequisites
2. Activate the `hledger_preprocessor` conda environment
3. Clear and recreate the working directory
4. Run `hledger_preprocessor --preprocess-assets`
5. Run `hledger-flow import`
6. Generate balance reports and plots with `hledger_plot`

Add `--randomize` to anonymise amounts in the plots.

---

## B. hledger CLI Basics

### B.1 Creating a starter journal

```sh
mkdir -p ~/finance
cat > ~/finance/start_pos/2024_complete.journal << EOF
; Starting position journal
2024-01-01 Opening balances
    Assets:Bank:Checking     EUR 1000.00
    Equity:Opening Balances
EOF
```

Point `file_names.start_journal_filepath` in your config to this file
(relative to `root_finance_path`).

### B.2 Common hledger commands

```sh
# Balance in Euros (converts all currencies)
hledger bal -X EUR -f ~/finance/working_dir/all-years.journal

# Assets only
hledger bal -X EUR assets

# Monthly breakdown with averages and total
hledger balance -M -A -b 2024-05 -T -X EUR

# Forecast (if periodic transactions defined)
hledger balance -M -A -b 2024-05 --forecast -T -X EUR

# Exclude equity
hledger balance -M -A -b 2024-05 -T assets expenses liabilities -X EUR
```

### B.3 CLI flag reference

| Flag | Meaning |
|------|---------|
| `-X EUR` | Convert all amounts to EUR |
| `cur:EUR` | Only include EUR transactions |
| `balance` | Show account balances |
| `-M` | Monthly granularity |
| `-A` | Show averages |
| `-b DATE` | Begin from date |
| `-T` | Show totals |
| `--forecast` | Include periodic transaction forecasts |

---

## C. hledger_preprocessor CLI

All actions require `--config <path>`:

```sh
hledger_preprocessor --config ~/finance/config.yaml <action>
```

### Actions

| Flag | Short | Description |
|------|-------|-------------|
| `--new-setup` | `-n` | Create directory structure for a new account |
| `--preprocess-csvs` | `-o` | Convert bank CSVs to hledger-flow format (requires `-p`) |
| `--preprocess-assets` | `-s` | Preprocess exported asset CSVs |
| `--generate-rules` | `-r` | Generate `.rules` file for hledger-flow |
| `--tui-label-receipts` | `-t` | Label receipt images in the TUI |
| `--make-ai-labels` | `-a` | Use AI (Donut model) to label receipts |
| `--improve-manual-labels` | `-i` | Review/improve existing manual labels |
| `--edit-receipt` | `-e` | Edit a receipt (rotate/crop) in the TUI |
| `--link-receipts-to-transactions` | `-l` | Match receipts to bank transactions |
| `--quick-categorisation` | `-q` | Fast feedback on uncategorised transactions (requires `-o` and `-p`) |

---

## D. Receipt Workflow

1. **Rotate & crop** — `--edit-receipt` opens the OpenCV TUI. Arrow keys move
   crop corners (10% steps), Alt switches corners, `r` rotates, Enter saves.

2. **Label** — `--tui-label-receipts` opens the urwid TUI where you enter
   amount, date, store, category, and payment account for each receipt.

3. **Match to transactions** — `--link-receipts-to-transactions` matches
   labelled receipts to bank CSV rows using date window (`matching_algo.days`),
   amount tolerance (`matching_algo.amount_range`), and optional day/month swap.

---

## E. Developer Instructions

### E.1 Setup

```sh
conda env create --file environment.yml
conda activate hledger_preprocessor
pip install -e .
pre-commit install
```

### E.2 Tests

```sh
python -m pytest                                           # all tests
python -m pytest test/unit -v                              # unit only
python -m pytest test/e2e -v                               # end-to-end only
python -m pytest test/e2e/test_gif_2b_label_receipt.py -v  # single test
```

Test structure:

```
test/
├── conftest.py          # shared fixtures (temp_finance_root)
├── unit/                # pure logic tests
├── integration/         # multi-component tests with fixtures
├── e2e/                 # full workflow tests (GIF generation)
├── fixtures/            # test data (categories, configs, receipts, etc.)
└── helpers/             # assertions, generators, seeders
```

### E.3 GIFs & User Stories Site

```sh
# Set up the demo environment first
python -m gifs.automation.setup_test_environment

# Build options
./build_userstories.sh --gifs                        # re-record all GIFs
./build_userstories.sh --gif 2b_label_receipt        # re-record one GIF
./build_userstories.sh --site --serve                # build site + serve on :8059
./build_userstories.sh --gif 2b_label_receipt --site --serve  # GIF + site + serve
./build_userstories.sh --dry-run                     # preview what would run
./build_userstories.sh --help                        # all options
```

Each GIF demo lives in `gifs/<name>/` with a `generate.sh`, `recordings/`, and
`output/`. The Python automation modules are in `gifs/automation/`.

### E.4 Publish pip package

```sh
rm -rf build dist
python -m build
pip install -e .                  # local install
python3 -m twine upload dist/*   # upload to PyPI
```

### E.5 Sphinx documentation

```sh
pip install -e .
cd docs
pip install -r requirements.txt
make html
# View at docs/build/html/index.html
```

Add manual documentation as `.md` files in `docs/source/manual_documentation/`
and reference them in `docs/source/manual.rst`.

---

## F. Receipt-Transaction Matching Algorithm

For each receipt:

1. Find all accounts involved with the receipt
2. Get the receipt's transaction date and amount
3. For each relevant account, find transactions within `matching_algo.days`
   days that match `matching_algo.amount_range` tolerance
4. If exactly 1 match: auto-link
5. If 0 matches and `days_month_swap` is true: retry with month/day swapped
6. If 0 matches still: prompt user to widen margins or check data
7. If 2-14 matches: rank by weighted closeness score (date 50%, amount 30%,
   time 20%) and let user pick
8. If 15+ matches: prompt user to narrow margins

---

## G. AI Model Installation (CUDA/NVIDIA)

Below are commands for setting up CUDA for the Donut receipt OCR model.
These may be outdated — check NVIDIA's website for current versions.

```sh
sudo apt install build-essential gcc-12 g++-12
conda install libgcc
nvidia-smi

# Download CUDA from: https://developer.nvidia.com/cuda-downloads
# Follow the instructions for your OS/architecture
```
