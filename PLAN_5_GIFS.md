# Plan: 5 GIF Demo Sequence

This plan outlines the implementation of 5 short demonstration GIFs that together explain the full hledger-preprocessor workflow using a **single coherent story** with **shared test fixtures**.

## The Story

> Alice has a bank account at Triodos and pays for groceries at Ekoplaza.
> She wants to track her spending with hledger, including receipt images.

**Single transaction used throughout:**

- **Date:** 2025-01-15
- **Amount:** -€42.17
- **Shop:** Ekoplaza (groceries)
- **Payment:** Card (Triodos bank account)

______________________________________________________________________

## Overview

| #   | GIF Name                  | CLI/Action                        | Duration | Status                     |
| --- | ------------------------- | --------------------------------- | -------- | -------------------------- |
| 1   | `01_setup_config`         | Display `config.yaml`             | ~15s     | TODO                       |
| 2   | `02_add_category`         | Display `categories.yaml`         | ~10s     | TODO                       |
| 3   | `03_label_receipt`        | `--edit-receipt` TUI              | ~30s     | EXISTS (edit_receipt)      |
| 4   | `04_match_receipt_to_csv` | `--link-receipts-to-transactions` | ~15s     | TODO                       |
| 5   | `05_run_pipeline`         | `./start.sh`                      | ~20s     | EXISTS (start_sh_pipeline) |

______________________________________________________________________

## Shared Test Fixture

All 5 GIFs use the same fixture based on `test/fixtures/config_templates/1_bank_1_wallet.yaml`:

```yaml
# Bank: Triodos checking account with CSV input
# Wallet: EUR physical (cash, derived from receipts)
# Transaction: 2025-01-15, -€42.17, Ekoplaza
```

**Files in fixture:**

| File                           | Purpose                                                |
| ------------------------------ | ------------------------------------------------------ |
| `config.yaml`                  | Account configuration (triodos bank + EUR wallet)      |
| `categories.yaml`              | Spending categories including `groceries:ekoplaza`     |
| `triodos_2025.csv`             | Bank CSV: `15-01-2025,NL123,-42.17,debit,Ekoplaza,...` |
| `dummy_receipt.jpg`            | Receipt image to label                                 |
| `groceries_ekoplaza_card.json` | Labelled receipt (card payment €42.17, matches CSV)    |
| `2024_complete.journal`        | Opening balances: €1000 checking                       |

______________________________________________________________________

## GIF 1: `01_setup_config`

**Purpose:** Show how to configure bank account + wallet

**Narrative:**

> "First, tell hledger-preprocessor about your bank accounts"

**Actions:**

1. Display header: "Step 1: Configure your accounts"
1. Show `config.yaml` with syntax highlighting (using Python `rich` library)
1. Highlight key sections with annotations:
   - `account_configs:` → "Define your bank accounts"
   - Bank account (triodos) with `input_csv_filename`
   - Wallet account (no CSV, derived from receipts)
   - `dir_paths:` → "Where files are stored"

**Implementation:**

- `gifs/01_setup_config/generate.sh`
- `gifs/automation/setup_config_demo.py`

______________________________________________________________________

## GIF 2: `02_add_category`

**Purpose:** Show how to add spending categories

**Narrative:**

> "Define your spending categories in categories.yaml"

**Actions:**

1. Display header: "Step 2: Define categories"
1. Show `categories.yaml` with syntax highlighting
1. Highlight the tree structure:
   ```yaml
   groceries:
     ekoplaza: {}    # ← This is what we'll use
     supermarket: {}
   repairs:
     bike: {}
   ```
1. Explain: "Categories become hledger accounts: `expenses:groceries:ekoplaza`"

**Implementation:**

- `gifs/02_add_category/generate.sh`
- `gifs/automation/add_category_demo.py`

______________________________________________________________________

## GIF 3: `03_label_receipt`

**Purpose:** Show TUI for labelling receipt images

**Narrative:**

> "Label your receipt with date, shop, amount, and payment method"

**Actions:**

1. Display header: "Step 3: Label your receipt"
1. Run `hledger_preprocessor --config config.yaml --edit-receipt`
1. TUI shows receipt image
1. Fill fields:
   - Date: 2025-01-15
   - Shop: Ekoplaza
   - Category: groceries:ekoplaza
   - Amount: 42.17
   - Payment: card (triodos account)
1. Save → creates `groceries_ekoplaza_card.json`

**Implementation:**

- **REUSE**: `gifs/edit_receipt/` (rename folder to `03_label_receipt/`)
- Update `receipt_editor.py` if needed to match story data

______________________________________________________________________

## GIF 4: `04_match_receipt_to_csv`

**Purpose:** Show automatic receipt-to-CSV matching

**Narrative:**

> "Automatically link receipts to bank transactions"

**Actions:**

1. Display header: "Step 4: Match receipt to bank transaction"
1. Show inputs side-by-side:
   ```
   Bank CSV (triodos_2025.csv):        Receipt Label (groceries_ekoplaza_card.json):
   ─────────────────────────────       ──────────────────────────────────────────────
   Date: 15-01-2025                    Date: 2025-01-15
   Amount: -42.17                      Amount: 42.17
   Payee: Ekoplaza                     Shop: Ekoplaza
   ```
1. Run `hledger_preprocessor --config config.yaml --link-receipts-to-transactions`
1. Show output: "Found 1 match → auto-linked (no TUI needed)"
1. Show updated receipt JSON now contains `csv_transaction` reference

**Key behavior (from code analysis):**

- `len(matches) == 1` → `auto_link_receipt()` - automatic, no TUI
- `len(matches) == 0` → `handle_no_matches()` - TUI prompt
- `len(matches) < 15` → `handle_few_matches()` - TUI selection

**Implementation:**

- `gifs/04_match_receipt_to_csv/generate.sh`
- `gifs/automation/match_receipt_demo.py`

______________________________________________________________________

## GIF 5: `05_run_pipeline`

**Purpose:** Show full pipeline producing journals + plots

**Narrative:**

> "Run the complete pipeline with ./start.sh"

**Actions:**

1. Display header: "Step 5: Run the pipeline"
1. Show what we have so far:
   - Config ✓
   - Categories ✓
   - Labelled receipt ✓
   - Receipt linked to CSV ✓
1. Run pipeline steps:
   - `hledger_preprocessor --preprocess-assets` → Creates asset CSVs
   - `hledger-flow import` → Creates journal files
   - `hledger_plot` → Creates SVG plots
1. Show outputs:
   - `all-years.journal` with the transaction
   - `hledger_plots/*.svg` sankey diagram

**Implementation:**

- **REUSE**: `gifs/start_sh_pipeline/` (rename folder to `05_run_pipeline/`)
- Update `start_sh_demo.py` if needed

______________________________________________________________________

## File Structure

```
gifs/
├── 01_setup_config/
│   ├── generate.sh
│   ├── output/
│   └── recordings/
├── 02_add_category/
│   ├── generate.sh
│   ├── output/
│   └── recordings/
├── 03_label_receipt/          # Renamed from edit_receipt
│   ├── generate.sh
│   ├── output/
│   └── recordings/
├── 04_match_receipt_to_csv/
│   ├── generate.sh
│   ├── output/
│   └── recordings/
├── 05_run_pipeline/           # Renamed from start_sh_pipeline
│   ├── generate.sh
│   ├── output/
│   └── recordings/
├── automation/
│   ├── setup_config_demo.py   # NEW
│   ├── add_category_demo.py   # NEW
│   ├── match_receipt_demo.py  # NEW
│   ├── receipt_editor.py      # EXISTS
│   └── start_sh_demo.py       # EXISTS
└── scripts/
    └── common.sh              # EXISTS
```

______________________________________________________________________

## E2E Test

```python
# test/e2e/test_gif_sequence.py

import pytest


class TestGifSequence:
    """Test all 5 GIFs in sequence with shared fixture (single coherent story)."""

    @pytest.fixture(scope="class")
    def demo_finance_root(self, temp_finance_root):
        """Shared fixture: Alice's Triodos account + Ekoplaza receipt."""
        return temp_finance_root

    def test_01_setup_config(self, demo_finance_root):
        """Config file exists and is valid."""
        config_path = demo_finance_root["config_path"]
        assert config_path.exists()
        # Run setup_config_demo, assert GIF created

    def test_02_add_category(self, demo_finance_root):
        """Categories file contains groceries:ekoplaza."""
        categories_path = demo_finance_root["root"] / "categories.yaml"
        content = categories_path.read_text()
        assert "ekoplaza" in content

    def test_03_label_receipt(self, demo_finance_root):
        """Receipt labelling produces valid JSON."""
        # Run receipt_editor demo
        # Assert groceries_ekoplaza_card.json created

    def test_04_match_receipt_to_csv(self, demo_finance_root):
        """Matching auto-links receipt to CSV (1 match)."""
        # Run --link-receipts-to-transactions
        # Assert receipt JSON contains csv_transaction reference

    def test_05_run_pipeline(self, demo_finance_root):
        """Full pipeline produces journals + plots."""
        # Run start_sh_demo
        # Assert all-years.journal exists
        # Assert hledger_plots/*.svg exists
```

______________________________________________________________________

## Implementation Order

1. **Update shared fixture** - Ensure `1_bank_1_wallet.yaml` and `conftest.py` have all data for the story
1. **GIF 1** - `01_setup_config` (simple: display config with colors)
1. **GIF 2** - `02_add_category` (simple: display categories with colors)
1. **GIF 4** - `04_match_receipt_to_csv` (most novel: show matching logic)
1. **Rename existing** - `edit_receipt` → `03_label_receipt`, `start_sh_pipeline` → `05_run_pipeline`
1. **Write E2E test** - `test_gif_sequence.py`

______________________________________________________________________

## Dependencies

- `rich` library (for syntax-highlighted YAML/JSON display in GIFs 1, 2, 4)
- Existing: `asciinema`, `agg`, `gifsicle`
