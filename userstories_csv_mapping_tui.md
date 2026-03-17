# CSV Column Mapping TUI — User Stories & Specification

> Purpose: Fully specify the interactive terminal TUI that maps CSV columns to
> hledger transaction fields, so it can be rebuilt in urwid, Haskell (brick), or
> any other framework without re-asking design questions.

---

## 1. High-Level Flow

The TUI is a **split-pane terminal UI** (top: scrollable CSV table, bottom:
questions/choices). It walks the user through an 8-step wizard:

| # | Step ID          | Description                                  | Interactive? |
|---|------------------|----------------------------------------------|-------------|
| 0 | account_holder   | Ask account holder name                      | Always      |
| 1 | bank             | Ask bank / exchange name                     | Always      |
| 2 | account_type     | Ask account type                             | Always      |
| 3 | base_currency    | Ask default currency (validated enum)        | Always      |
| 4 | mapping          | Template detect + split decision + col map   | Always      |
| 5 | decimal_format   | Auto-detect or ask eu/dot format             | Sometimes   |
| 6 | preview          | Show parsed transaction preview              | Always      |
| 7 | summary          | Show mapping summary + confirm save          | Always      |

**Back-navigation** (Escape) goes back one step. Non-interactive steps (e.g.
auto-detected decimal format) are skipped when going back.

---

## 2. Layout

### US-2.1: Split-Pane Layout

```
┌────────────────────────────────────────────┐
│ CSV: filename.csv  (15 cols, 100 rows)     │  ← Title bar (bold, dark bg)
│  ↑ 2 row(s) above                         │  ← Row overflow indicator
│  Timezone  Date       Time    Type    ...  │  ← Header (bold, word-wrapped)
│  UTC       2024-01-01 10:00   buy    ...   │  ← Data rows (alternating col bg)
│  UTC       2024-01-02 11:30   sell   ...   │
│  the_date… tendered…  -       -      ...   │  ← Mapping row (green text)
│  ↓ 5 row(s) below                         │  ← Row overflow indicator
│────────────────────────────────────────────│  ← Divider (dim dashes)
│  (answer log, dimmed)                      │  ← Bottom pane
│  (current question / choice list)          │
│  (hint bar: keyboard shortcuts)            │
└────────────────────────────────────────────┘
```

- **Top pane**: Scrollable CSV table (headers + data + optional mapping row).
- **Bottom pane**: Fixed 8 lines. Shows answer log (dimmed), current
  question/choice, error messages, and keyboard hints.
- The bottom pane content scrolls if it exceeds available space (most recent
  entries kept visible).

### US-2.2: Column Styling

- Columns use alternating background colors (even: dark teal `#003040`,
  odd: dark purple `#400050`).
- Headers are **bold white**.
- Data cells are **white**.
- The mapping row values are **green** (or **dim** if the value is `-`/empty).
- Dimmed rows/columns use the terminal dim attribute.

### US-2.3: Overflow Indicators

- `< ` (dim) on the left when columns are scrolled right (`col_offset > 0`).
- ` >` (dim) on the right when columns extend beyond the terminal width.
- `↑ N row(s) above` when rows are scrolled down.
- `↓ N row(s) below` when more rows exist below the visible area.

### US-2.4: Column Highlighting

When a column is being mapped, it gets an **underline** style in the table.
The underline applies to every row (header, data, mapping) for that column
index.

---

## 3. Dynamic Column Widths

### US-3.1: Data-Driven Column Widths

Column width = `min(max(longest_data_value, longest_header_word, mapping_row_value), 30)`.

- The **header text is NOT included** in the max — only data row values and the
  mapping row value count.
- The **minimum** width is the length of the longest single word in the header
  (so at least one word fits per line).
- Maximum column width is capped at 30 characters.

### US-3.2: Header Word-Wrapping

Headers wrap to fit the data-driven column width. Word-wrapping splits on
spaces. If a single word is longer than the column width, it occupies its own
line (no mid-word breaking). Multi-line headers add extra rows to the header
area. All header columns share the same number of display lines (padded with
blank lines if shorter).

### US-3.3: Dynamic Width Recomputation

When the mapping row changes (a field is assigned or negated), column widths
are **recomputed** from `max(base_data_width, mapping_value_length)`. If any
width changed, headers are re-wrapped. This happens via `set_mapping_row()`.

Example: Column "Amount" has data values `"50.00"` (5 chars), but mapping row
gets `"tendered_amount_out"` (19 chars) → column widens to 19.

### US-3.4: Cell Truncation

If a cell value exceeds the column width, it is truncated with an ellipsis
(`…`) at position `width - 1`.

---

## 4. Table Scrolling

### US-4.1: Alt+Arrow Scrolling

During any question/choice, the user can scroll the table:
- **Alt+Left / Alt+Right**: Scroll columns left/right.
- **Alt+Up / Alt+Down**: Scroll rows up/down.

Scrolling triggers a full redraw.

### US-4.2: Auto-Scroll to Highlighted Column

When a column is selected for mapping (via `ask_choice` or `ask_column_select`
or `ask_negate_table`), the table auto-scrolls horizontally to ensure the
highlighted column is visible.

---

## 5. Keyboard Input

### US-5.1: Raw Terminal Mode

The TUI operates in raw terminal mode (no line buffering, no echo). The cursor
is hidden during the TUI session and restored on exit.

### US-5.2: Key Bindings (Global)

| Key             | Action                                      |
|-----------------|---------------------------------------------|
| Alt+Arrow keys  | Scroll table (all input modes)              |
| Escape          | Go back to previous step/column             |
| Ctrl+C          | Abort (KeyboardInterrupt)                   |

### US-5.3: Key Bindings (Text Input — `ask_string`)

| Key       | Action                          |
|-----------|---------------------------------|
| Enter     | Confirm (use default if empty)  |
| Backspace | Delete last character            |
| Printable | Append character to input        |
| Escape    | Go back                          |

### US-5.4: Key Bindings (Choice Selection — `ask_choice`)

| Key       | Action                           |
|-----------|----------------------------------|
| Up/Down   | Move selection cursor            |
| Enter     | Confirm selection                |
| Escape    | Go back to previous column       |

### US-5.5: Key Bindings (Column Selection — `ask_column_select`)

| Key         | Action                             |
|-------------|------------------------------------|
| Left/Right  | Move to previous/next column       |
| Enter       | Confirm selected column            |
| Escape      | Go back                            |

### US-5.6: Key Bindings (Negate Table — `ask_negate_table`)

| Key           | Action                                      |
|---------------|---------------------------------------------|
| Left/Right    | Jump to previous/next numeric column        |
| Up/Down       | Same as Left/Right                          |
| Enter/Space   | Toggle negation on current column           |
| Tab           | Confirm and finish negate step              |
| Escape        | Go back to re-ask last column mapping       |

---

## 6. Step Details

### US-6.0: Account Holder (Step 0)

- Text input: `"Account holder (e.g. 'at')"`
- Free text, no validation beyond non-empty.
- Result stored as `state["account_holder"]`.

### US-6.1: Bank (Step 1)

- Text input: `"Bank / exchange (e.g. 'bitvavo')"`
- Free text.
- Result stored as `state["bank"]`.

### US-6.2: Account Type (Step 2)

- Text input: `"Account type (e.g. 'checking', 'trading')"`
- Free text.
- Result stored as `state["account_type"]`.

### US-6.3: Base Currency (Step 3)

- Text input: `"Default currency (e.g. EUR, USD, BTC)"`
- **Validated** against the Currency enum. Case-insensitive (auto-uppercased).
- On invalid input: shows error `"Unknown currency 'X'. Valid: BTC, XMR, ..."`,
  removes the bad log entry, and re-asks.
- Valid currencies: BTC, XMR, ZCASH, ETH, WBTC, LINK, RVN, GRAMS, LITER, EUR,
  USD, GBP, GOLD, SILVER, CASH.
- Result stored as `state["base_currency"]` (Currency enum value).

### US-6.4: Mapping (Step 4) — Template Detection + Split + Column Mapping

This is a compound step with sub-flows:

#### US-6.4.1: Template Detection

- On entry, check if CSV headers match a known template (e.g. Bitvavo).
- Template detection: the template's `detection_headers` must all be present
  in the CSV headers.
- If detected: ask `"Detected {name} CSV format. Apply template? [Y/n]"`.
  - If Yes: apply template's column mappings, split column, decimal format,
    and groups. Show the last group's mapping row in the table. Skip to next
    step.
  - If No: continue to manual mapping.

#### US-6.4.2: Split Decision

- Ask: `"Split CSV by a type column? (for mixed row types) [Y/n]"`
- If Yes → enter split flow (US-6.4.3).
- If No → enter simple mapping flow (US-6.4.5).

#### US-6.4.3: Split Column Selection

- Use `ask_column_select`: user picks the split column with Left/Right arrows.
- Show unique values found in that column:
  `"Unique values: buy, sell, deposit"`.

#### US-6.4.4: Split Group Definition

- **Loop** asking for group values until all unique values are assigned:
  - `"Group N values (comma-separated, remaining: deposit, buy, sell)"`
  - Validates that entered values exist in the unique values set.
  - Validates that entered values haven't been assigned to a prior group.
  - On error: shows message, removes bad log entry, re-asks.
- **Back-navigation**: Escape undoes the previous group definition
  (returns its values to the remaining pool). Escape at group 1 propagates
  GoBack to the main loop.
- After all values assigned: shows `"N groups defined. Now map columns for each group."`
- Then runs column mapping (US-6.4.5) for each group sequentially. After the
  first group, subsequent groups are **pre-filled** from the previous group's
  mapping as defaults.

#### US-6.4.5: Column Mapping (per-column choice loop)

For each CSV column (0 to N-1):

1. **Highlight** the column in the table (underline).
2. **Auto-scroll** so the column is visible.
3. Show in the bottom pane:
   - Column header + sample values (first 3, quoted).
   - Auto-mapper suggestion with confidence score (if any).
   - The **field choice list** (see US-7).
4. User picks a field with Up/Down + Enter.
5. The mapping row in the table updates to show the chosen field name.
6. The verbose log entry from the choice is **suppressed** (the mapping row
   serves as visual summary instead).
7. Move to next column.

**Back-navigation**: Escape undoes the current column and goes back to the
previous column. At column 0, propagates GoBack to the caller.

**Pre-filling from previous group**: When `previous_chosen` is provided, each
column's default selection is set to the previous group's choice for that
column. The user can quickly press Enter to confirm or change.

#### US-6.4.6: Row Dimming in Split Mode

When mapping columns for a split group, rows that do NOT belong to the current
group are **dimmed** (all columns in those rows use the dim attribute). A row
belongs to the group if `row[split_column].strip()` is in the group's values
tuple. This dimming persists through both the column choice phase and the
negate phase.

#### US-6.4.7: Negate Step (after all columns mapped)

After the last column is mapped:
1. **Reset table scroll to left** (`col_offset = 0`).
2. Enter the negate table (US-6.4.8).
3. On GoBack from negate: undo last column choice, re-ask last column.

#### US-6.4.8: Negate Table Interaction

- Only columns mapped to numeric fields are navigable:
  `tendered_amount_out`, `received_amount`, `fee_amount`, `quote_price`,
  `exchange_rate`, `balance_after`.
- Skipped (unmapped) columns are **dimmed** in the table during this step.
- Current numeric column is highlighted (underline).
- Left/Right jumps between numeric columns only.
- Enter/Space toggles negation. When negated:
  - The mapping row shows `field(neg)` (e.g. `tendered_amount_out(neg)`).
  - Data values in that column are shown with **flipped signs** (e.g. `50` →
    `-50`, `-3.14` → `3.14`).
- Tab confirms. The `negate:` prefix is added to the field name internally
  (e.g. `negate:tendered_amount_out`).
- Bottom pane shows: `"Negate columns: Col N Header → field [x]"` and
  hints: `"←→ prev/next numeric col  Enter/Space=toggle  Tab=done  Esc=back"`.

#### US-6.4.9: Validation After Mapping

After column mapping + negate completes, validate:
- **Date is mapped**: Either `the_datetime` alone, or both `the_date_only` and
  `the_time_only`. Error if only one of date/time without the other.
- **Amount is mapped**: `tendered_amount_out` must be mapped.

If validation fails, show error message and raise GoBack so the user can fix.

#### US-6.4.10: Re-edit After Preview Rejection

When the user rejects the preview (step 6), the flow returns to step 4
(mapping) with `_reedit_mapping = True`. In this mode:
- Template detection and split questions are **skipped**.
- Column mapping re-enters with existing choices as **pre-fill defaults**.
- The user can tweak individual column mappings without starting over.

### US-6.5: Decimal Format (Step 5)

- **Auto-detection**: Examine numeric column values for comma/dot patterns.
  - `"."` with >2 decimal digits → `"dot"`.
  - `","` with ≤2 decimal digits and no dot → `"eu"`.
  - Both present: compare last occurrence positions.
- If auto-detected: show in log as `"Decimal format: dot"`. This step is
  **non-interactive** (skipped when going back).
- If template already set it: same behavior (non-interactive).
- If not detectable: ask `"Decimal format: 'eu' (1.234,56) or 'dot' (1,234.56)"` with default `"dot"`. This step is **interactive**.

### US-6.6: Preview (Step 6)

- Parse up to 5 sample rows using the mapping and decimal format.
- For split mode: route each row to its group's mapping based on the split
  column value.
- Display format per row:
  ```
  [type] date                   amount currency description           extras
  [buy]  2024-01-01 10:00:00          -500.0 EUR   Buy order               quote_price=42000.0
  ```
- After display: ask `"Does the preview look correct? [Y/n]"`.
  - Yes → proceed to summary.
  - No → raise PreviewRejected → go back to mapping re-edit (US-6.4.10).
  - Escape → GoBack to previous step (decimal format if interactive, else mapping).

### US-6.7: Summary (Step 7)

- Show: `"Mapping summary:"`, account info, split column (if any).
- The mapping row in the table shows the final mapping.
- Ask: `"Save this mapping to config? [Y/n]"`.
  - Yes → save to YAML config and exit.
  - No → exit without saving ("`Aborted — nothing saved.`").

---

## 7. Field Choices

The field choice list presented for each column:

| Field name                  | Display label                                            | Group            |
|-----------------------------|----------------------------------------------------------|------------------|
| *(None)*                    | Skip                                                     |                  |
| `the_date_only`             | date (Date — combine with time)                          | date/time group  |
| `the_time_only`             | time (Time — combine with date)                          | date/time group  |
| `the_datetime`              | datetime (Datetime — single column)                      | datetime group   |
| *(separator)*               |                                                          |                  |
| `tendered_amount_out`       | tendered_amount_out (Amount out of this account)         |                  |
| `payment_currency`          | payment_currency (Currency out of this account)          |                  |
| *(separator)*               |                                                          |                  |
| `received_amount`           | received_amount (Amount into this account)               |                  |
| `received_currency`         | received_currency (Currency into this account)           |                  |
| *(separator)*               |                                                          |                  |
| `quote_price`               | quote_price (Price per unit in quote currency)           | quote group      |
| `exchange_rate`             | exchange_rate (1 quote = X base — inverse of quote price)| exchange group   |
| `quote_currency`            | quote_currency (Currency of quote/exchange rate)         |                  |
| *(separator)*               |                                                          |                  |
| `fee_amount`                | fee_amount (Fee amount)                                  |                  |
| `fee_currency`              | fee_currency (Fee currency)                              |                  |
| *(separator)*               |                                                          |                  |
| `description`               | description (Description)                                |                  |
| `other_party_name`          | other_party_name (Other party name)                      |                  |
| `other_party_account_name`  | other_party_account_name (Other party account)           |                  |
| `transaction_code`          | transaction_code (Transaction code Debit/Credit)         |                  |
| `balance_after`             | balance_after (Balance after transaction)                |                  |
| `bic`                       | bic (BIC Bank Identifier Code)                           |                  |

### US-7.1: Separators

Separators (`__sep__`) render as blank lines in the choice list. They are not
selectable — Up/Down arrow skips them.

### US-7.2: Mutual Exclusivity

- **date/time group** (`the_date_only`, `the_time_only`) and **datetime group**
  (`the_datetime`) are mutually exclusive. If any from one group is used,
  fields in the other group are grayed out.
- **quote group** (`quote_price`) and **exchange group** (`exchange_rate`) are
  mutually exclusive. Same graying behavior.

### US-7.3: Already-Used Fields

Fields that are already mapped to another column show `(unavailable)` and are
dimmed. If the user selects an unavailable field:
- Show: `"'field' mapped to col N 'Header'. Enter=replace, ↑↓=pick other"`.
- Enter: unmaps the old column (sets it to Skip) and assigns this field here.
- Up/Down: continues browsing the list.
- Any other key: cancels.

### US-7.4: Choice Display

```
  Column 3: Type   "buy", "sell", "deposit"
  Auto: transaction_code (Transaction code) [100%]
▶ Skip                                          ← Green bold arrow = selected
    date (Date — combine with time)
    time (Time — combine with date)
    datetime (Datetime — single column)

    tendered_amount_out (Amount out of this account)
    ...
```

The selected item has a green bold `▶` arrow. Unavailable items selected show a
red bold `▶` arrow with `(unavailable)`.

---

## 8. Auto-Mapper Integration

### US-8.1: Header Pattern Matching

The auto-mapper matches CSV headers against known patterns (case-insensitive):

| Field                      | Patterns                                             |
|----------------------------|------------------------------------------------------|
| `the_date`                 | date, datum, transaction date, booking date, valuta  |
| `tendered_amount_out`      | amount, bedrag, received / paid amount               |
| `description`              | description, omschrijving, memo, narrative, details, remark |
| `other_party_name`         | name, naam, counterparty, payee, beneficiary         |
| `other_party_account_name` | account, iban, rekening, contra account              |
| `transaction_code`         | type, transaction type, af bij, debit/credit         |
| `balance_after`            | balance, saldo, balance after                        |
| `bic`                      | bic, swift                                           |
| `payment_currency`         | currency, valuta, quote currency                     |

- Exact match → confidence 1.0.
- Substring match → confidence 0.7.
- Each field maps to at most one column (first match wins).

### US-8.2: Value-Type Fallback

For unmapped columns after header matching:
- If values look like dates (regex `^\d{2,4}[-/\.]\d{1,2}[-/\.]\d{1,4}$`,
  >50% match) → propose `the_date` (confidence 0.5).
- If values look numeric (>50% parseable as float) → propose
  `tendered_amount_out` (confidence 0.4).

### US-8.3: Default Selection in Choice List

- Auto-mapper's `the_date` maps to `the_datetime` as the initial default in
  the choice list.
- If the proposed field is already used by another column, default falls back
  to Skip (index 0).

---

## 9. Template System

### US-9.1: Template Structure

A template defines:
- `name`: Display name (e.g. "Bitvavo").
- `decimal_format`: `"eu"` or `"dot"`.
- `split_column`: 0-based column index, or None.
- `groups`: List of `TemplateGroup`, each with:
  - `values`: Tuple of row-type values that belong to this group.
  - `column_mappings`: List of `(field_name_or_empty, hledger_name)` per CSV
    column.
- `detection_headers`: Frozenset of header strings that must all be present.

### US-9.2: Template Detection

Check each template in `ALL_TEMPLATES` list. First template whose
`detection_headers` are all present in the CSV headers wins. Return `None` if
no match.

### US-9.3: Currently Defined Templates

**Bitvavo** (15 columns):
- Detection headers: `"Quote Currency"`, `"Quote Price"`, `"Fee currency"`,
  `"Received / Paid Currency"`, `"Received / Paid Amount"`.
- Split column: 3 (Type).
- Groups:
  - Deposits (`deposit`, `rebate`, `campaign_new_user_incentive`).
  - Trades (`buy`, `sell`).
- Decimal format: `"dot"`.

---

## 10. Mapping Row

### US-10.1: Mapping Row in Table

An extra row is appended below the data rows in the CSV table. It shows the
chosen field name for each column. Display rules:
- Unmapped columns show `-`.
- Mapped columns show the field name (e.g. `tendered_amount_out`).
- Negated columns show `field(neg)` (e.g. `tendered_amount_out(neg)`).

### US-10.2: Mapping Row Styling

- Mapped field names: **green** text on alternating column background.
- Unmapped `-`: **dim** text.
- Respects `dim_cols` during the negate step.

### US-10.3: Mapping Row Lifecycle

- Initialized to empty strings when entering column mapping.
- Updated after each column choice.
- Updated after negate toggle.
- Shown during summary step (last group's mapping for split mode).
- Cleared after save confirmation.

---

## 11. Row & Column Dimming

### US-11.1: Row Dimming (Split Groups)

When mapping columns for a split group, rows not in the group are dimmed.
Determination: `row[split_column].strip() not in group_values`. Dimmed rows
have **all columns** rendered with dim style. This persists through both the
column choice phase and the negate phase. Cleared after the group's mapping
completes.

### US-11.2: Column Dimming (Negate Step)

During the negate step, columns that are **skipped** (unmapped) are dimmed.
This helps the user focus on numeric columns that can be negated. Cleared after
the negate step completes.

---

## 12. Back-Navigation

### US-12.1: Step-Level Back

Escape during any step goes back to the previous step. The answer log is
rolled back to the snapshot taken at the start of that step. Non-interactive
steps (auto-detected decimal format) are skipped.

### US-12.2: Column-Level Back (within mapping)

Escape during column mapping goes back to the previous column. The previous
column's choice is undone (removed from `used_fields`), and the mapping row
is rebuilt. At column 0, GoBack propagates to the main step loop.

### US-12.3: Group-Level Back (within split flow)

- During group value definition: Escape undoes the previous group definition.
- During per-group column mapping: Escape at group 0 col 0 undoes that group
  and goes back. At group > 0, goes back to re-map the previous group.

### US-12.4: Preview Rejection

When the user answers "No" to the preview confirmation:
- PreviewRejected is raised.
- The flow jumps back to the mapping step with `_reedit_mapping = True`.
- All column mappings are preserved as pre-fill defaults.
- Template detection and split questions are skipped.

### US-12.5: Negate Back

Escape during the negate table goes back to re-ask the last column. The negate
state is discarded.

---

## 13. Sign Flipping (Negate)

### US-13.1: Flip Sign Display

When a column is negated, its values in the CSV table are shown with flipped
signs:
- `"50"` → `"-50"`
- `"-3.14"` → `"3.14"`
- Non-numeric values are unchanged.

### US-13.2: Negate Prefix in Config

Negated fields are stored with `negate:` prefix (e.g. `negate:tendered_amount_out`).
This prefix is preserved through config name translation and YAML persistence.

---

## 14. Config Output

### US-14.1: Field Name Translation

Internal TUI field names are translated to config field names:
- `the_date_only` → `the_date`
- `the_time_only` → `the_time`
- `the_datetime` → `the_date`
- All others → same name.

The `negate:` prefix is preserved through translation.

### US-14.2: Hledger Name Defaults

Each field has a default hledger CSV column name:
- `the_date` / `the_date_only` / `the_datetime` → `"date"`
- `the_time_only` → `"time"`
- `tendered_amount_out` → `"amount"`
- `description` → `"description"`
- `payment_currency` → `"currency"`
- All others → `""` (empty).

### US-14.3: AccountConfig Object

The TUI produces an `AccountConfig` with:
- `account`: Account(base_currency, account_holder, bank, account_type).
- `input_csv_filename`: basename of the CSV file.
- `csv_column_mapping`: `CsvColumnMapping` with tuple of `(field, hledger_name)` pairs.
- `tnx_date_columns`: `CsvColumnMapping` filtered to only `the_date`, `the_time`,
  and `description` entries.
- `split_column`: int or None.
- `split_groups`: tuple of `SplitGroup` objects (each with values, csv_column_mapping,
  tnx_date_columns).
- `decimal_format`: `"eu"`, `"dot"`, or None.

### US-14.4: YAML Persistence

Saved to `config.yaml` under `account_configs` list. Each entry:

```yaml
account_configs:
  - input_csv_filename: bitvavo.csv
    base_currency: EUR
    account_holder: at
    bank: bitvavo
    account_type: trading
    decimal_format: dot
    split_column: 3
    csv_column_mapping: null   # null when split mode
    tnx_date_columns: null     # null when split mode
    split_groups:
      - values: [deposit, rebate]
        csv_column_mapping:
          - ["", ""]
          - [the_date, date]
          - [the_time, time]
          - ["", ""]
          - [payment_currency, currency]
          - [tendered_amount_out, amount]
          ...
        tnx_date_columns:
          - [the_date, date]
          - [the_time, time]
          - [description, description]
      - values: [buy, sell]
        csv_column_mapping:
          ...
```

Non-split mode:
```yaml
  - input_csv_filename: bank.csv
    base_currency: EUR
    account_holder: at
    bank: ing
    account_type: checking
    decimal_format: eu
    csv_column_mapping:
      - [the_date, date]
      - ["", ""]
      - [tendered_amount_out, amount]
      - [description, description]
    tnx_date_columns:
      - [the_date, date]
      - [description, description]
```

If an entry for the same `input_csv_filename` already exists, it is **replaced**
(not duplicated). The save action shows `"Updated"` vs `"Saved"` accordingly.

---

## 15. CSV Reading

### US-15.1: CSV Preview

- Read the full CSV file.
- Auto-detect encoding via `chardet` / `detect_file_encoding`.
- Use `csv.Sniffer().has_header()` to determine if the first row is a header.
  If sniffer fails, assume header.
- If no header detected: generate `Column_0`, `Column_1`, ... as header names.
- Return: headers, sample_rows (first 10 data rows), total_rows, filepath.

---

## 16. Terminal Cleanup

### US-16.1: On Exit

- Restore original terminal settings (from `termios.tcgetattr` saved at init).
- Show cursor (`\033[?25h`).
- Clear screen (`\033[2J\033[H`).
- Print save confirmation or "Aborted" message in normal terminal mode.

### US-16.2: On Error / Ctrl+C

- The `finally` block ensures terminal is always restored, even on exceptions.

---

## 17. Answer Log

### US-17.1: Answer Log Rendering

The answer log is a list of styled strings shown dimmed in the bottom pane.
It records completed answers (e.g. `"Account holder: at"`) so the user has
context of previous choices.

### US-17.2: Log Snapshots for Rollback

At the start of each step, the current length of the answer log is recorded.
When going back, the log is truncated to that snapshot.

### US-17.3: Verbose Log Suppression

During column mapping, the verbose `"Col N 'Header' → field"` entry that
`ask_choice` adds is **immediately removed** after each choice returns. The
mapping row in the table serves as the visual summary instead.

---

## 18. Error Handling

### US-18.1: Currency Validation Error

Invalid currency input: `"Unknown currency 'X'. Valid: BTC, XMR, ..."`.
The bad log entry is removed. Re-asks until valid.

### US-18.2: Group Value Validation Errors

- Unknown values: `"Unknown values: foo, bar"`.
- Already assigned: `"Already assigned: buy"`.
Bad log entry removed, re-asks.

### US-18.3: Mutually Exclusive Field Error

Selecting a grayed-out field: `"'field' is unavailable. ↑↓ to pick another."`.
Does not accept the selection.

### US-18.4: Mapping Validation Error

Missing required fields shown as joined error:
`"Date must be mapped: ... | 'tendered_amount_out' (Amount) must be mapped."`.
Raises GoBack for the user to fix.

---

## 19. Decimal Format Detection

### US-19.1: Detection Algorithm

Examine all numeric column values across mapped numeric fields:
1. Has `.` without `,` and >2 decimal digits → `"dot"`.
2. Has `,` without `.` and ≤2 decimal digits → `"eu"`.
3. Has both: compare last occurrence — if `,` is last → `"eu"`, else → `"dot"`.
4. If no conclusive evidence → `None` (will ask the user).

---

## 20. Preview Parsing

### US-20.1: Row Parsing Logic

For each sample row (up to 5):
1. Route to the correct mapping (via split column if applicable).
2. For each mapped column:
   - Numeric fields: parse with decimal format, apply negate if prefixed.
   - Date fields: store as-is.
   - Time fields: store as-is (concatenated with date for display).
   - Other fields: store as-is.
3. Format: `[type] date  amount currency description  extras`.
   - Extras show `key=value` for quote_price, exchange_rate, received_amount,
     fee_amount.

---

## Appendix A: Data Types

```
CsvPreview:
    headers: List[str]
    sample_rows: List[List[str]]
    total_rows: int
    filepath: str

AutoMapping:
    csv_column_index: int
    csv_header: str
    proposed_field: Optional[str]
    proposed_hledger_name: str
    confidence: float  # 0.0 - 1.0

CsvTemplate:
    name: str
    decimal_format: str       # "eu" or "dot"
    split_column: Optional[int]
    groups: List[TemplateGroup]
    detection_headers: FrozenSet[str]

TemplateGroup:
    values: Tuple[str, ...]
    column_mappings: List[Tuple[Optional[str], str]]

AccountConfig:
    account: Account
    input_csv_filename: Optional[str]
    csv_column_mapping: Optional[CsvColumnMapping]
    tnx_date_columns: Optional[CsvColumnMapping]
    split_column: Optional[int]
    split_groups: Optional[Tuple[SplitGroup, ...]]
    decimal_format: Optional[str]

SplitGroup:
    values: Tuple[str, ...]
    csv_column_mapping: CsvColumnMapping
    tnx_date_columns: CsvColumnMapping

CsvColumnMapping:
    csv_column_mapping: Tuple[Tuple[str, str], ...]

Account:
    base_currency: Currency
    account_holder: str
    bank: str
    account_type: str
```

## Appendix B: ANSI Color Codes Used

| Constant   | Code            | Usage                              |
|------------|-----------------|-------------------------------------|
| BOLD       | `\033[1m`       | Headers, prompts, selected items    |
| DIM        | `\033[2m`       | Dimmed rows/cols, log, hints        |
| UNDERLINE  | `\033[4m`       | Highlighted column                  |
| FG_WHITE   | `\033[97m`      | Normal cell text                    |
| FG_GREEN   | `\033[92m`      | Confirmed answers, mapping row      |
| FG_RED     | `\033[91m`      | Errors, unavailable items           |
| FG_CYAN    | `\033[96m`      | Input prompts, column info          |
| FG_YELLOW  | `\033[93m`      | Negate toggle mark                  |
| FG_MAGENTA | `\033[95m`      | (Available, currently unused)       |
| BG_DARK    | `\033[100m`     | Title bar background                |
| COL_EVEN   | `\033[48;5;24m` | Even column background (dark teal)  |
| COL_ODD    | `\033[48;5;54m` | Odd column background (dark purple) |
