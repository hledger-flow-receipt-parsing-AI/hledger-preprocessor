# Split Mode & Crypto Trading

## Split Mode Data Flow

```
raw CSV (e.g. bitvavo.csv)
  → split by Type column (col index from split_column)
  → each split group has its own csv_column_mapping
  → GenericCsvTransaction.to_hledger_dict() produces per-row dicts
  → dicts merged (key-union across groups, missing cols = None)
  → written to preprocessed CSV (2-preprocessed/YEAR/file.csv)
  → hledger reads CSV + .rules file → journal entries
```

### Key Implementation Details

- `AccountConfig.get_hledger_csv_column_names()` returns the **union** of all groups' columns for the `fields` directive
- `export_to_csv.py` uses this canonical column order, fills missing keys with `None`
- `AccountConfig.parse_csv_rows()` groups rows by `row[split_column]` value, looks up the matching `SplitGroup`, applies that group's mapping

## Bitvavo Config Example

```yaml
- input_csv_filename: bitvavo.csv
  base_currency: EUR
  split_column: 3          # Type column
  split_groups:
  - values: [sell]
    csv_column_mapping:
    - [payment_currency, base_currency]        # col maps to base_currency
    - [negate:tendered_amount_out, amount]      # negated
    - [received_currency, received_currency]
    - [received_amount, received_amount]
    ...
  - values: [buy]
    csv_column_mapping:
    - [received_currency, received_currency]    # swapped vs sell
    - [received_amount, received_amount]
    - [payment_currency, base_currency]
    - [negate:tendered_amount_out, amount]
    ...
  linked_accounts:
  - account_holder: at
    bank: triodos
    account_type: checking
    transfer_types: [deposit]
```

The sell group swaps which raw CSV column maps to `payment_currency` vs `received_currency`, so `base_currency` ends up as the crypto ticker (BTC), enabling the buy/sell rule discrimination.

## Preprocessed Data by Transaction Type

| Field | Buy | Sell | Deposit | Rebate |
|-------|-----|------|---------|--------|
| `base_currency` | EUR (fiat) | BTC (crypto) | — | EUR |
| `amount` | 3999.44 (EUR spent) | 0.052 (BTC sold) | — | 0.0 |
| `received_currency` | BTC | EUR | EUR | EUR |
| `received_amount` | 0.067 | 3874.66 | 5000.0 | 10.0 |
| `quote_price` | 59147.0 | 74600.0 | — | — |

## The `currency` → `base_currency` Rename

hledger's `fields` directive treats `currency` as magic — it becomes a global currency prefix for ALL amounts. This broke crypto cost notation. Renamed to `base_currency` in all relevant files: `auto_mapper.py`, `templates.py`, `generate_rules_content.py`, `GenericTransactionWithCsv.py`, `AccountTransaction.py`, config, and tests.

## Key Files

| File | Role |
|------|------|
| `csv_mapping/auto_mapper.py` | `DEFAULT_HLEDGER_NAMES`, auto-mapping |
| `csv_mapping/templates.py` | Bitvavo template with 4 split groups |
| `generics/GenericTransactionWithCsv.py` | `to_hledger_dict()` — produces hledger CSV row |
| `config/AccountConfig.py` | `get_hledger_csv_column_names()` — union of groups |
| `csv_parsing/export_to_csv.py` | Key-union logic, writes preprocessed CSV |
| `rules/generate_rules_content.py` | Generates `.rules` file |
