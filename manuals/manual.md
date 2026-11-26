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

______________________________________________________________________

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
- **categorisation** — `quick: true/false` (unused); the rules live in `categorisation_rules.yaml` (section H)
- **csv_encoding** — e.g. `utf-8`
- **matching_algo** — controls how receipts are matched to bank transactions
  (date window, amount range, month/day swap)

### A.3 Run

```sh
./start.sh --config ~/finance/config.yaml
```

This will:

1. Parse the config and validate prerequisites
1. Activate the `hledger_preprocessor` conda environment
1. Clear and recreate the working directory
1. Run `hledger_preprocessor --preprocess-assets`
1. Run `hledger-flow import`
1. Generate balance reports and plots with `hledger_plot`

Add `--randomize` to anonymise amounts in the plots.

______________________________________________________________________

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

| Flag         | Meaning                                |
| ------------ | -------------------------------------- |
| `-X EUR`     | Convert all amounts to EUR             |
| `cur:EUR`    | Only include EUR transactions          |
| `balance`    | Show account balances                  |
| `-M`         | Monthly granularity                    |
| `-A`         | Show averages                          |
| `-b DATE`    | Begin from date                        |
| `-T`         | Show totals                            |
| `--forecast` | Include periodic transaction forecasts |

______________________________________________________________________

## C. hledger_preprocessor CLI

All actions require `--config <path>`:

```sh
hledger_preprocessor --config ~/finance/config.yaml <action>
```

### Actions

| Flag                              | Short | Description                                                          |
| --------------------------------- | ----- | -------------------------------------------------------------------- |
| `--new-setup`                     | `-n`  | Create directory structure for a new account                         |
| `--preprocess-csvs`               | `-o`  | Convert bank CSVs to hledger-flow format (requires `-p`)             |
| `--preprocess-assets`             | `-s`  | Preprocess exported asset CSVs                                       |
| `--generate-rules`                | `-r`  | Generate `.rules` file for hledger-flow                              |
| `--tui-label-receipts`            | `-t`  | Label receipt images in the TUI                                      |
| `--make-ai-labels`                | `-a`  | Auto-label receipt images using the AI extraction pipeline           |
| `--improve-manual-labels`         | `-i`  | Review/improve existing manual labels                                |
| `--edit-receipt`                  | `-e`  | Edit a receipt (rotate/crop) in the TUI                              |
| `--link-receipts-to-transactions` | `-l`  | Match receipts to bank transactions                                  |
| `--categorise-transactions`       | `-q`  | TUI: one rule per uncategorised bank transaction group (see H)       |
| `--check-categorisation`          |       | Report rows no rule matches and rows several rules match             |
| `--train [names]`                 |       | Train hledger-ai models, incl. `csv-linear` (transaction categories) |
| `--train-models`                  |       | Train/retrain AI models on accumulated labelled data                 |
| `--model <name>`                  |       | Which model to train: `setfit`, `qwen-lora`, or `all` (default)      |
| `--force-retrain`                 |       | Force retraining even if the dataset hasn't changed                  |

______________________________________________________________________

## H. Categorisation Rules

Every bank transaction must satisfy **exactly one** rule, whatever the order
of the rules (issue #25). The rules are data, not Python:
`categorisation_rules.yaml` in the finance root, next to `categories.yaml`.

```yaml
version: 1
rules:
- id: 12
  direction: debit            # debit | credit
  match:                      # every condition must hold
  - {field: payee, op: contains, value: VOORBEELD SUPERMARKT}
  unless:                     # the rule does not fire when a group holds
  - - {field: description, op: contains, value: TO GO}
  target: groceries:voorbeeld # a category path, or account:<holder:bank:type>
  source: tui
```

Fields: `payee`, `description`, `counter_account`, `own_account`, `amount`
(the float as Python prints it, e.g. `42.17`), `date`
(`YYYY-MM-DD-HH-MM-SS`), `text` (any of the three text fields). Ops:
`contains`, `starts_with`, `equals`, `any_of` (a list). Matching is case-
insensitive unless `case_sensitive: true`.

### H.1 Adding rules: the TUI

```bash
hledger_preprocessor --categorise-transactions --config config.yaml   # or -q
```

Uncategorised rows are grouped by payee (else description, else counter
account), largest group first. For each group the screen shows the rows, a
draft rule (field, op, value: editable), what the draft would do to every
row of the root, the category field (with the category tree behind Alt+n)
and the AI suggestions of the `csv-linear` model when one is trained.

| Key             | Action                                                                     |
| --------------- | -------------------------------------------------------------------------- |
| Enter           | Save the rule (the file is written at once) and show the next              |
| Tab             | Complete the category: the common start of the matches, else               |
|                 | the highlighted (or first) match (`groceries:s` → `groceries:supermarket`) |
| Shift+Tab       | Switch between the value and the category                                  |
| ↑ / ↓           | Highlight a match (Enter takes it)                                         |
| Alt+a, Alt+b, … | Take the 1st, 2nd, … AI suggestion and save                                |
| Alt+n           | Category tree: pick or create a category                                   |
| Alt+f / Alt+o   | Change the field / the op of the draft                                     |
| Alt+s           | Skip this group (it comes back at the end)                                 |
| Alt+w           | This rule wins: the conflicting rules get an `unless`                      |
| Alt+y           | This rule yields: it gets an `unless` per conflicting rule                 |
| Alt+p           | Previous group                                                             |
| Esc             | Quit                                                                       |

A draft that also matches a row another rule already covers is refused:
the store stays one-hot by construction. Alt+w resolves it the way "most
specific wins" would when the draft is the specific one; Alt+y when the
existing rule is (a broad `payee contains X` next to an existing
`payee contains X via Y`). Both are data, never order.

### H.2 Checking

`--check-categorisation` (and the pipeline pre-flight) lists every row no
rule matches (`UncategorisedTransactionError`) and every row several rules
match (`MultipleMatchError`). Hand edits of the YAML are caught here.

### H.3 Converting an old `private_logic.py`

```bash
python -m hledger_preprocessor.categorisation.rule_based.convert_private_logic \
    --config config.yaml [--private-logic path] [--keep]
```

Keeps every classification of the if/return code (the first matching block
used to win: later rules get an `unless` with the winner's conditions), gives
conditions that only ever matched the amount or the date that field, verifies
every row, and moves the Python file to `<finance root>/backup/`.

### H.4 The transaction model

`hledger_preprocessor --train csv-linear --config config.yaml` trains a light
text model on the rows the rules categorise (per finance root, private, in
`~/.hledger-ai/<root>-<hash>/`), evaluated on time-ordered folds against the
most-frequent-category baseline; `python -m hledger_ai --config config.yaml --status` shows it next to the receipt models. The TUI prefills the best
category per group with it, and the AI column of the preprocessed CSVs holds
its top category. A root without rules yet can borrow another root's model:

```yaml
ai:
  transaction_model_root: /home/you/finance
```

______________________________________________________________________

## D. Receipt Workflow

1. **Rotate & crop** — `--edit-receipt` opens the OpenCV TUI. Arrow keys move
   crop corners (10% steps), Alt switches corners, `r` rotates, Enter saves.

1. **Label** — `--tui-label-receipts` opens the urwid TUI where you enter
   amount, date, store, category, and payment account for each receipt.

1. **Match to transactions** — `--link-receipts-to-transactions` matches
   labelled receipts to bank CSV rows using date window (`matching_algo.days`),
   amount tolerance (`matching_algo.amount_range`), and optional day/month swap.

______________________________________________________________________

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

______________________________________________________________________

## F. Receipt-Transaction Matching Algorithm

For each receipt:

1. Find all accounts involved with the receipt
1. Get the receipt's transaction date and amount
1. For each relevant account, find transactions within `matching_algo.days`
   days that match `matching_algo.amount_range` tolerance
1. If exactly 1 match: auto-link
1. If 0 matches and `days_month_swap` is true: retry with month/day swapped
1. If 0 matches still: prompt user to widen margins or check data
1. If 2-14 matches: rank by weighted closeness score (date 50%, amount 30%,
   time 20%) and let user pick
1. If 15+ matches: prompt user to narrow margins

______________________________________________________________________

## G. Local AI Models

The `hledger-ai` package provides self-hosted AI features via
[Ollama](https://ollama.com/):

- **Receipt extraction** — VLM (Qwen3-VL-2B) extracts date, shop, items,
  totals from receipt images and suggests them in the TUI.
- **Transaction classification** — SetFit few-shot classifier + Qwen3-0.6B
  zero-shot cascade assigns spending categories to bank CSV transactions.

### G.1 Install Ollama and pull models

```sh
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull the required models
ollama pull qwen3-vl:2b    # Vision-language model for receipts
ollama pull qwen3:0.6b     # Text model for classification/category
```

### G.2 Configure AI in config.yaml

Add an `ai:` section to your config:

```yaml
ai:
  ollama_url: "http://localhost:11434"
  models_dir: "~/.hledger-ai/models"
  feedback_dir: "~/.hledger-ai/feedback"
  vlm_model: "qwen3-vl:2b"
  text_model: "qwen3:0.6b"
  auto_accept_threshold: 0.9
  suggest_threshold: 0.3
```

### G.3 AI-assisted receipt labelling

When `ai:` is configured, `--tui-label-receipts` automatically runs the
extraction pipeline on each receipt image and pre-populates TUI fields
with AI suggestions (date, shop, items, totals, category). Suggestions
appear in the sidebar — press **Alt+U** to accept an AI suggestion.

### G.4 Auto-label receipts (non-interactive)

```sh
hledger_preprocessor --make-ai-labels --config config.yaml
```

Runs the extraction pipeline on all unlabelled receipt images and saves
JSON labels. Already-labelled images are skipped.

### G.5 Train AI models

Train the transaction classifier on your accumulated labelled data:

```sh
# Train all eligible models (SetFit + Qwen LoRA)
hledger_preprocessor --train-models --config config.yaml

# Train only SetFit (fast, needs 8+ examples per category)
hledger_preprocessor --train-models --model setfit --config config.yaml

# Train only Qwen LoRA (needs 50+ examples, GPU recommended)
hledger_preprocessor --train-models --model qwen-lora --config config.yaml

# Force retrain even if the dataset hasn't changed
hledger_preprocessor --train-models --force-retrain --config config.yaml
```

Training uses a SHA-256 hash of the sorted, deduplicated dataset to skip
retraining when the data hasn't changed. Use `--force-retrain` to override.

Optional dependencies for training:

```sh
pip install hledger-ai[setfit]     # SetFit few-shot classifier
pip install hledger-ai[finetune]   # Qwen LoRA fine-tuning (requires GPU)
```

### G.6 Correction feedback loop

When you override an AI suggestion in the TUI, the correction is logged
to `~/.hledger-ai/feedback/corrections.jsonl`. These corrections are
automatically included in the training dataset the next time you run
`--train-models`, continuously improving accuracy.
