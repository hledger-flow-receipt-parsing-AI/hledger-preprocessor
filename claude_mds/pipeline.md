# Pipeline: `start.sh`

## Project

- **Root**: `/home/a/git/git/hledger/hledger-preprocessor`
- **Conda env**: `hledger_preprocessor` (Python 3.12)
- **Entry point**: `./start.sh --config /path/to/config.yaml`

## Pipeline Phases

### Phase 0: Shell prerequisites + config loading

1. Sources `process_yaml_prerequisites.sh` (checks `yq` mikefarah v4, `jq`)
2. Sources `proces_config_accounts.sh` (defines `process_accounts()`, `proces_config_accounts()`)
3. Parses CLI: `--config <path>` (required), `--randomize` (optional)
4. Loads paths from `config.yaml` via `yq`: `FINANCE_DIR`, `WORKING_DIR`, `START_JOURNAL_FILEPATH`, `RECEIPT_IMAGES_DIR`, `RECEIPT_LABELS_DIR`, `ASSET_TRANSACTION_CSVS`
5. Activates conda env
6. **Wipes `$WORKING_DIR`** (`rm -rf`) and recreates it

### Phase 1: Validate config + set up accounts

`validate_config` → `proces_config_accounts()`:
- For each account with a `.csv`, runs `hledger_preprocessor --new-setup` to create `$WORKING_DIR/import/` directory structure with `preprocess` and `.rules` files
- Then `hledger_preprocessor --link-receipts-to-transactions` to link receipt labels to account transactions

### Phase 2: Match transactions

```bash
hledger_preprocessor --config "$CONFIG" --match-transactions
```

Expands to `--match-receipts` + `--match-csv-to-csv`. Non-fatal (errors logged as warnings).

### Phase 3: Preprocess assets

```bash
hledger_preprocessor --config "$CONFIG" --preprocess-assets
```

Processes accounts without CSVs (wallets, physical assets). **Fatal on uncategorised transactions.**

### Phase 4: hledger-flow import

```bash
cd "$WORKING_DIR" && hledger-flow import
```

Runs each account's `preprocess` script (calls `hledger_preprocessor --preprocess-csvs`), applies `.rules` files, produces `all-years.journal`.

### Phase 5: Starting position + reports

1. Adds `include $START_JOURNAL_FILEPATH` to `all-years.journal`
2. `hledger bal -X EUR`
3. `hledger_plot` for visualizations

## CLI Entry Points

| Flag | Function | File |
|------|----------|------|
| `--map-csv <file>` | `run_csv_mapping_tui()` | `csv_mapping/mapping_tui.py` |
| `--new-setup` | `manage_creating_new_setup()` | `management/main_manager.py` |
| `--link-receipts-to-transactions` | `manage_matching_manual_receipt_objs_to_account_transactions()` | `management/main_manager.py` |
| `--match-transactions` | expands to `--match-receipts` + `--match-csv-to-csv` | `__main__.py` |
| `--match-receipts` | `manage_batch_match_receipts()` | `management/main_manager.py` |
| `--match-csv-to-csv` | `manage_match_csv_to_csv()` | `management/main_manager.py` |
| `--preprocess-csvs` | `manage_preprocessing_csvs()` | `management/main_manager.py` |
| `--preprocess-assets` | `manage_preprocessing_assets()` | `management/main_manager.py` |
| `--generate-rules` | `manage_generating_rules()` | `management/main_manager.py` |
| `--tui-label-receipts` | `manage_creating_receipt_img_labels_with_tui()` | `management/main_manager.py` |

## Config Structure

```yaml
account_configs:
  - input_csv_filename: "bitvavo.csv"
    account_holder: at
    bank: bitvavo
    account_type: trading
    base_currency: EUR
    csv_column_mapping: null        # null when split mode
    tnx_date_columns: null
    split_column: 3
    split_groups: [...]
    decimal_format: dot             # "dot" or "eu"
    linked_accounts: [...]

dir_paths:
  root_finance_path: "~/finance"
  working_subdir: "working_dir"
  receipt_images_input_dir: "receipt_images_input"
  receipt_labels_dir: "receipt_labels"
  asset_transaction_csvs_dir: "asset_transaction_csvs"

file_names:
  start_journal_filepath: "start_pos/2024_complete.journal"
  categories_filename: "categories.yaml"

matching_algo:
  days: 2
  amount_range: 0
```

## Generated File Structure

After Phase 1, each account has:
```
$WORKING_DIR/import/<holder>/<bank>/<type>/
  ├── 1-in/              # Input CSV (copied here, per-year subdirs)
  ├── 2-preprocessed/    # Preprocessed CSV (after preprocess runs)
  ├── 3-journal/         # Generated journal files
  ├── preprocess         # The preprocessing script
  └── *.rules            # hledger rules file
```

## Common Failure Points

1. **Config loading**: Missing YAML fields, CSV not found, `yq` version mismatch (needs mikefarah v4)
2. **`--new-setup`**: `preprocess` script embeds Python in `python3 -c "..."` — double-quotes in Python code break the shell string
3. **Receipt matching**: Date format mismatches, amount rounding
4. **Asset preprocessing**: Uncategorised transactions (fix in `categorisation/rule_based/private_logic.py`)
5. **hledger-flow import**: `.rules` syntax errors, magic field names, additive rules
6. **Balance report**: Missing `include`, currency conversion failures

## Run Commands

```bash
# Full pipeline
source ~/miniconda3/etc/profile.d/conda.sh && conda activate hledger_preprocessor
TERM=xterm ./start.sh --config /home/a/finance/config.yaml

# Full pipeline with demo data
python -m gifs.automation.setup_test_environment && ./start.sh --config /tmp/hledger_demo/config.yaml

# Individual phases
hledger_preprocessor --config /path/to/config.yaml --new-setup
hledger_preprocessor --config /path/to/config.yaml --match-transactions
hledger_preprocessor --config /path/to/config.yaml --preprocess-assets
cd $WORKING_DIR && hledger-flow import

# Tests
python -m pytest test/ -v
```
