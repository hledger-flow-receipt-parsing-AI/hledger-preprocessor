# Key Files Reference

## Core Pipeline

| File | Purpose |
|------|---------|
| `start.sh` | Main pipeline orchestrator |
| `process_yaml_prerequisites.sh` | Validates yq/jq/config |
| `proces_config_accounts.sh` | Iterates accounts, runs `--new-setup` + `--link-receipts-to-transactions` |
| `src/.../__ main__.py` | CLI entry point, dispatches to managers |

## Config

| File | Purpose |
|------|---------|
| `src/.../config/load_config.py` | Config loading and validation |
| `src/.../config/Config.py` | Config dataclass, YAML parsing for split_column/split_groups/decimal_format |
| `src/.../config/AccountConfig.py` | AccountConfig + SplitGroup dataclasses, `parse_csv_rows()`, `get_hledger_csv_column_names()` |

## Management / Orchestration

| File | Purpose |
|------|---------|
| `src/.../management/main_manager.py` | All `manage_*` functions, `_should_skip_withdrawal_transaction()` |
| `src/.../management/helper.py` | `preprocess_generic_csvs()`, `preprocess_asset_csvs()` |

## CSV Mapping TUI

| File | Purpose |
|------|---------|
| `src/.../csv_mapping/mapping_tui.py` | Full TUI (~3500 lines) |
| `src/.../csv_mapping/templates.py` | Template definitions + detection |
| `src/.../csv_mapping/auto_mapper.py` | Header pattern matching, `DEFAULT_HLEDGER_NAMES` |
| `src/.../csv_mapping/csv_reader.py` | `read_csv_preview()` |

## Parsing & Export

| File | Purpose |
|------|---------|
| `src/.../generics/parse_generic_tnx_with_csv.py` | Decimal-format-aware CSV row parsing, negate support |
| `src/.../generics/GenericTransactionWithCsv.py` | `to_hledger_dict()` — transaction → hledger CSV row |
| `src/.../csv_parsing/csv_to_transactions.py` | `csv_to_transactions()`, `parse_encoded_input_csv()` |
| `src/.../csv_parsing/export_to_csv.py` | Key-union logic, writes preprocessed CSV |

## Rules Generation

| File | Purpose |
|------|---------|
| `src/.../rules/generate_rules_content.py` | Generates `.rules` file: crypto trade rules, withdrawal rules, deposit rules |

## Transaction Objects

| File | Purpose |
|------|---------|
| `src/.../TransactionObjects/ProcessedTransaction.py` | `to_hledger_dict()` — maps transactions/withdrawal metadata to CSV columns |
| `src/.../TransactionObjects/Receipt.py` | Receipt + WithdrawalMetadata dataclasses |
| `src/.../TransactionObjects/AccountTransaction.py` | Receipt-based transaction → hledger dict |

## Categorisation

| File | Purpose |
|------|---------|
| `src/.../categorisation/rule_based/private_logic.py` | User categorization rules (ATM detection, etc.) |

## Receipt Labelling TUI (separate project)

| File | Purpose |
|------|---------|
| `tui-image-labeller/.../WithdrawalQuestions.py` | Withdrawal question definitions |
| `tui-image-labeller/.../reconfiguration.py` | Post-account question injection, withdrawal toggle, prefill |
| `tui-image-labeller/.../account_parser.py` | `parse_withdrawal_answers()` → WithdrawalMetadata |
| `tui-image-labeller/.../create_receipt.py` | `build_receipt_from_answers()` |
