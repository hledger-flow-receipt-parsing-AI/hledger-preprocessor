# Features 1+5+6+7: CSV Split-by-Type, Exchange Rate Toggle, Templates, Preview

## Context
The CSV mapping TUI works for simple bank CSVs (Triodos) but not for exchange CSVs (Bitvavo) because:
- Bitvavo has mixed row types (deposit, buy, sell, rebate) with different column semantics — need split-by-type
- The parser hardcodes European decimal format which destroys dot-decimal values
- Users need `exchange_rate` as alternative to `quote_price`
- No way to verify parsed amounts before committing config

## Key constraint
**One CSV → one AccountConfig.** No changes to `csv_to_transactions.py` or other src code beyond `AccountConfig.py` and the TUI/template/parser files. The split logic lives entirely in a new `AccountConfig` method that converts sub-CSVs into a single unified transaction list.

## Data model for split-by-type

A single `AccountConfig` stores:
- `split_column: Optional[int]` — 0-based index of the column to split on (e.g. 3 for "Type")
- `split_groups: Optional[Tuple[SplitGroup, ...]]` — each group has: values (e.g. `("buy", "sell")`), its own `CsvColumnMapping`, its own `tnx_date_columns`
- `decimal_format: Optional[str]` — `"eu"` or `"dot"` or `None` (legacy=eu)

When `split_column` is `None`, the existing `csv_column_mapping` + `tnx_date_columns` are used for all rows (backward compatible, no split).

When `split_column` is set, `process_transactions()` calls a new method on `AccountConfig` that:
1. Groups rows by `row[split_column]` value
2. Looks up which `SplitGroup` each value belongs to
3. Applies that group's `csv_column_mapping` to parse each row
4. Returns a flat list of `GenericCsvTransaction`

## Implementation Order

### Step 1: Data model — `SplitGroup` + AccountConfig fields

**`src/hledger_preprocessor/config/AccountConfig.py`**:
- Add `SplitGroup` frozen dataclass:
  ```python
  @dataclass(frozen=True)
  class SplitGroup:
      values: Tuple[str, ...]           # e.g. ("buy", "sell")
      csv_column_mapping: CsvColumnMapping
      tnx_date_columns: CsvColumnMapping
  ```
- Add 3 optional fields to `AccountConfig`:
  ```python
  split_column: Optional[int] = None
  split_groups: Optional[Tuple[SplitGroup, ...]] = None
  decimal_format: Optional[str] = None
  ```
- Add new method `parse_csv_rows(rows, account_config) -> List[GenericCsvTransaction]`:
  - If `split_column is None`: delegate to `parse_generic_bank_transaction()` for each row using `self.csv_column_mapping` (existing behavior, just relocated)
  - If `split_column is not None`: group rows by `row[split_column]`, find matching `SplitGroup`, parse each row with that group's mapping
  - Returns unified flat list of transactions

**`src/hledger_preprocessor/config/Config.py`** — In `create_account_config_from_yaml()`:
- Parse `split_column`, `split_groups` (list of `{values: [...], csv_column_mapping: [...], tnx_date_columns: [...]}`) and `decimal_format` from YAML dict
- Pass to `AccountConfig(...)`

**YAML format:**
```yaml
- input_csv_filename: bitfavo.csv
  base_currency: EUR
  account_holder: at
  bank: bitvavo
  account_type: trading
  decimal_format: dot
  split_column: 3
  split_groups:
    - values: ["deposit", "rebate", "campaign_new_user_incentive"]
      csv_column_mapping: [["the_date", "date"], ["", ""], ...]
      tnx_date_columns: [["the_date", "date"]]
    - values: ["buy", "sell"]
      csv_column_mapping: [["the_date", "date"], ["", ""], ...]
      tnx_date_columns: [["the_date", "date"]]
  csv_column_mapping: null
  tnx_date_columns: null
```

### Step 2: Feature 5 — exchange_rate / quote_price mutual exclusivity

**`src/hledger_preprocessor/csv_mapping/mapping_tui.py`**:
- Add groups: `_QUOTE_PRICE_GROUP = {"quote_price"}`, `_EXCHANGE_RATE_GROUP = {"exchange_rate"}`
- Add `("exchange_rate", "exchange_rate (Exchange rate: 1 quote = X base)")` to FIELD_CHOICES after `quote_price`
- Extend `_is_grayed_out()` with the new mutual exclusivity check

**`src/hledger_preprocessor/csv_mapping/auto_mapper.py`** — Add `"exchange_rate": ""` to `DEFAULT_HLEDGER_NAMES`

**`src/hledger_preprocessor/generics/parse_generic_tnx_with_csv.py`** — Add `"exchange_rate"` to numeric field list

### Step 3: Decimal format in parser

**`src/hledger_preprocessor/generics/parse_generic_tnx_with_csv.py`** — Replace hardcoded European format:
```python
decimal_fmt = getattr(account_config, 'decimal_format', None)
if decimal_fmt == "dot":
    cleaned = value.replace(",", "")
elif decimal_fmt == "eu":
    cleaned = value.replace(".", "").replace(",", ".")
else:
    cleaned = value.replace(".", "").replace(",", ".")  # legacy default
```

### Step 4: Feature 1 — Split-by-type in the TUI

**`src/hledger_preprocessor/csv_mapping/mapping_tui.py`** — Modify `run_csv_mapping_tui()`:

After account details (holder, bank, type, currency), before column mapping:
1. Ask `"Split CSV by a type column? [Y/n]"`
2. If yes:
   - Show column headers with indices, ask which column (e.g. "3" for Type)
   - Read all unique values from sample rows for that column
   - Ask user to define groups: "Group 1 values (comma-separated):" → `deposit,rebate,campaign_new_user_incentive`
   - Ask "More groups? [Y/n]" → "Group 2 values:" → `buy,sell`
   - **Validate**: all unique values must be assigned to exactly one group
   - For **each group**: run the normal column mapping loop (`ask_choice` per column), producing a separate `csv_column_mapping` + `tnx_date_columns`
3. If no: run the single column mapping loop as today (no split)

The TUI produces either:
- `split_column=None, csv_column_mapping=<mapping>` (no split, backward compat)
- `split_column=3, split_groups=[SplitGroup(...), SplitGroup(...)], csv_column_mapping=None` (split mode)

Update `_save_to_config()` to persist `split_column`, `split_groups`, `decimal_format`.

### Step 5: Feature 6 — Template-based mapping

**New file: `src/hledger_preprocessor/csv_mapping/templates.py`**:
- `CsvTemplate` frozen dataclass: `name`, `decimal_format`, `split_column`, `groups` (list of `{values, column_mappings}`), `detection_headers`
- `BITVAVO_TEMPLATE` with two groups:
  - deposits: `["deposit", "rebate", "campaign_new_user_incentive"]` with simple mapping (date, time, skip Type, currency, amount, skip exchange cols, fee_currency, fee_amount, skip status, description=Transaction ID, skip address)
  - trades: `["buy", "sell"]` with full exchange mapping (date, time, skip Type, payment_currency, tendered_amount_out, quote_currency, quote_price, received_currency, received_amount, fee_currency, fee_amount, skip status, description=Transaction ID, skip address)
- `detect_template(headers) -> Optional[CsvTemplate]`
- `ALL_TEMPLATES` list

**`src/hledger_preprocessor/csv_mapping/mapping_tui.py`**:
- After `auto_map_columns()`, call `detect_template(preview.headers)`
- If detected: ask "Detected {name} format. Apply template? [Y/n]"
- If accepted: pre-fill split_column, groups, decimal_format — skip manual mapping
- If declined: proceed with normal flow

### Step 6: Feature 7 — Two-pass preview

**`src/hledger_preprocessor/csv_mapping/mapping_tui.py`** — Add helpers:
- `_parse_numeric(value, decimal_format)` — format-aware float parsing with auto-detect fallback
- `_build_preview_lines(preview, chosen_or_groups, decimal_format, split_column)` — parse sample rows, return formatted lines showing date, amount, currency, extra fields

After mapping is complete (either template or manual), before save confirmation:
- Build preview lines and append to `tui.answer_log`
- Show preview for each group if split, or for all rows if not
- `tui.ask_confirm("Does the preview look correct?")` — if no, raise error

## Files modified

| File | Change |
|------|--------|
| `config/AccountConfig.py` | `SplitGroup` dataclass, +3 optional fields, `parse_csv_rows()` method |
| `config/Config.py` | Parse `split_column`, `split_groups`, `decimal_format` from YAML |
| `csv_mapping/mapping_tui.py` | Split-by-type flow, template prompt, preview, exchange_rate toggle, `_save_to_config()` |
| `csv_mapping/auto_mapper.py` | `exchange_rate` in `DEFAULT_HLEDGER_NAMES` |
| `csv_mapping/templates.py` | **New** — template definitions + detection |
| `generics/parse_generic_tnx_with_csv.py` | Decimal-format-aware parsing, `exchange_rate` in numeric list |

## Verification
1. `--map-csv bitfavo.csv` → detects Bitvavo → apply template → preview shows deposits + trades correctly
2. `--map-csv bitfavo.csv` → decline template → manual split on col 3 → group deposits, group trades → map each → preview correct
3. `--new-setup` with saved config → `parse_csv_rows()` splits and parses all rows without crashes
4. Existing Triodos flow (no split, no decimal_format) → backward compatible
5. `python -m pytest test/ -v` — all tests pass


## Implemented UX improvements
- Column selector: `ask_column_select()` highlights columns in the table, navigates with left/right arrows, confirms with Enter
- Group segregation: all groups are collected first (Phase 1), then each group is mapped (Phase 2)
- Pre-fill: subsequent groups pre-select the previous group's mapping as defaults — user only changes what differs

- ensure the user can negate a column. from -5 to 5 or vice versa.
- Ensure the user goes back to the last question (of the filled data, instead of the previous question of do you want to prefill data) after: answering n on "  Does the preview look correct? [Y/n]: ".