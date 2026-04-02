# CSV Mapping TUI

## Overview

A standalone terminal TUI (`mapping_tui.py`) for mapping CSV columns to hledger transaction fields. Raw `termios`/`tty` with ANSI escape codes (no urwid). Split-pane layout: scrollable CSV table top, questions bottom.

**Entry point**: `hledger_preprocessor --map-csv <csv_file> --config <config.yaml>`

## Architecture

### Key Files

| File | Purpose |
|------|---------|
| `csv_mapping/mapping_tui.py` | Main TUI (~3500 lines): rendering, input, step loop, column mapping |
| `csv_mapping/templates.py` | Template definitions (Bitvavo) + `detect_template()` |
| `csv_mapping/auto_mapper.py` | Auto-maps CSV headers to field names by fuzzy matching |
| `csv_mapping/csv_reader.py` | `read_csv_preview()` — reads headers + sample rows |
| `config/AccountConfig.py` | `AccountConfig` + `SplitGroup` dataclasses, `parse_csv_rows()` |

### Data Model

```python
@dataclass(frozen=True)
class SplitGroup:
    values: Tuple[str, ...]
    csv_column_mapping: CsvColumnMapping
    tnx_date_columns: CsvColumnMapping

@dataclass(frozen=True, unsafe_hash=True)
class AccountConfig:
    account: Account
    input_csv_filename: Optional[str]
    csv_column_mapping: Optional[CsvColumnMapping]
    tnx_date_columns: Optional[CsvColumnMapping]
    split_column: Optional[int] = None
    split_groups: Optional[Tuple[SplitGroup, ...]] = None
    decimal_format: Optional[str] = None  # "dot" or "eu" or None (legacy=eu)
    linked_accounts: Optional[Tuple[LinkedAccount, ...]] = None
```

One CSV = one AccountConfig. Split logic lives in `AccountConfig.parse_csv_rows()`.

## Step Loop

| # | Step | Interactive? |
|---|------|-------------|
| 0 | `account_holder` | Always |
| 1 | `bank` | Always |
| 2 | `account_type` | Always |
| 3 | `base_currency` (validated enum) | Always |
| 4 | `mapping` (template detect + split + column map + negate) | Always |
| 5 | `linked_accounts` (inter-account transfer links) | Sometimes |
| 6 | `decimal_format` (auto-detect or ask) | Sometimes |
| 7 | `preview` (parsed sample rows) | Always |
| 8 | `summary` (confirm save) | Always |

State stored in `state: Dict[str, Any]`. `log_snapshots: List[int]` tracks answer log length per step for rollback.

## Implemented Features

### Split-by-Type
Mixed CSVs (e.g. Bitvavo: deposit, buy, sell, rebate) split by a type column. Each group gets its own column mapping.

### Template Detection
Auto-detects CSV format from headers (Bitvavo template exists). User can accept to skip manual mapping, or review/edit mappings.

### Column Negation
After all columns are mapped, a negate step lets the user flip signs on numeric columns. Stored as `negate:` prefix (e.g. `negate:tendered_amount_out`). Numeric columns: `tendered_amount_out`, `received_amount`, `fee_amount`, `quote_price`, `exchange_rate`, `balance_after`.

### Exchange Rate / Quote Price Toggle
Mutually exclusive: picking one grays out the other.

### Pre-fill Across Groups
When mapping subsequent split groups, previous group's choices are pre-filled as defaults.

### Two-Pass Preview
After mapping, parsed sample rows displayed for verification before saving.

### Linked Accounts
After mapping validation, if only one direction (in/out) is mapped, asks about inter-account links. Also available as a dedicated step 5.

### Config Loading
On startup, if config.yaml already has an entry for the CSV, offers to load it. Loaded config enters re-edit mode (skip metadata questions).

### Table Sort
During steps 0-3, Alt+S sorts the table by a user-chosen column.

## Go-Back Navigation

- `GoBack(Exception)` raised on Escape
- Per-step rollback via `log_snapshots`
- Per-column rollback within mapping step
- Per-group rollback within split flow
- Non-interactive steps skipped when going back
- Preview rejection (`PreviewRejected`) returns to mapping step with `_reedit_mapping = True` (preserves choices as defaults)

## Field Choices

| Field | Description |
|-------|-------------|
| Skip | Don't map this column |
| `the_date_only` | Date (combine with time) |
| `the_time_only` | Time (combine with date) |
| `the_datetime` | Datetime (single column) |
| `tendered_amount_out` | Amount out of this account |
| `payment_currency` | Currency out |
| `received_amount` | Amount into this account |
| `received_currency` | Currency in |
| `quote_price` | Price per unit (mutually exclusive with exchange_rate) |
| `exchange_rate` | 1 quote = X base (mutually exclusive with quote_price) |
| `quote_currency` | Currency of quote/exchange rate |
| `fee_amount` | Fee amount |
| `fee_currency` | Fee currency |
| `description` | Description |
| `other_party_name` | Other party name |
| `other_party_account_name` | Other party account |
| `transaction_code` | Debit/Credit |
| `balance_after` | Balance after transaction |
| `bic` | BIC code |
| `__custom__` | Create custom field name |

Date/time group and datetime group are mutually exclusive. Quote and exchange groups are mutually exclusive.

## Config Output

Field name translation: `the_date_only` → `the_date`, `the_time_only` → `the_time`, `the_datetime` → `the_date`. `negate:` prefix preserved.

Split mode: `split_column=N, split_groups=[...], csv_column_mapping=null`
Non-split: `split_column=null, csv_column_mapping=[...]`

Saved to `config.yaml` under `account_configs`. Existing entry for same filename is replaced.

## Layout

```
┌────────────────────────────────────────────┐
│ CSV: filename.csv  (15 cols, 100 rows)     │  Title bar
│  ↑ 2 row(s) above                         │  Overflow indicator
│  Header1   Header2   Header3   ...         │  Headers (bold, word-wrapped)
│  data      data      data      ...         │  Data rows (alternating col bg)
│  the_date  amount    -         ...         │  Mapping row (green)
│  ↓ 5 row(s) below                         │  Overflow indicator
│────────────────────────────────────────────│
│  (answer log, dimmed)                      │  Bottom pane (8 lines)
│  (current question / choice list)          │
│  (hint bar)                                │
└────────────────────────────────────────────┘
```

Navigation: Alt/Ctrl+Arrow to scroll table, Left/Right for column select, Up/Down for choices, Enter to confirm, Escape to go back.

## Known Bug: Go-Back from Preview

When preview is rejected, the step loop goes back through non-interactive decimal_format to the mapping step, which clears state, forcing full redo. The `interactive_steps` skip mechanism works but the mapping step's state clearing is too aggressive. Options:
- A: Don't clear `decimal_format` when re-entering mapping
- B: Preview rejection targets a more granular step
- C: Sub-menu on rejection: "What to change?"
- D: Force decimal_format to be interactive on re-entry
