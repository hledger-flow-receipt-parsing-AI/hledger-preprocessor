# CSV Mapping & Crypto Rules — Handover Document

## Status: Working

`./start.sh --config /home/a/finance/config.yaml` runs to completion, generates
correct hledger journal entries for all transaction types, and launches the Dash
plot server. All changes are committed (commit `b80bdfd`).

---

## 1. Architecture Overview

### Data Flow

```
raw CSV (bitvavo.csv)
  → split by Type column (col 4: buy/sell/deposit/rebate)
  → each split group has its own csv_column_mapping
  → GenericCsvTransaction.to_hledger_dict() produces per-row dicts
  → dicts merged (key-union across groups, missing cols = None)
  → written to preprocessed CSV (2-preprocessed/YEAR/bitvavo.csv)
  → hledger reads CSV + .rules file → journal entries
```

### Key Files

| File | Role |
|------|------|
| `src/.../csv_mapping/auto_mapper.py` | `DEFAULT_HLEDGER_NAMES` dict, auto-mapping logic |
| `src/.../csv_mapping/templates.py` | Bitvavo template with 4 split groups |
| `src/.../csv_mapping/mapping_tui.py` | TUI for interactive CSV column mapping (~3500 lines) |
| `src/.../generics/GenericTransactionWithCsv.py` | `to_hledger_dict()` — produces hledger CSV row from transaction |
| `src/.../config/AccountConfig.py` | `get_hledger_csv_column_names()` — union of all groups' columns |
| `src/.../csv_parsing/export_to_csv.py` | Key-union logic, writes preprocessed CSV |
| `src/.../rules/generate_rules_content.py` | Generates `.rules` file for hledger |
| `src/.../TransactionObjects/AccountTransaction.py` | Receipt-based transaction → hledger dict |
| `/home/a/finance/config.yaml` | User's live config with Triodos + Bitvavo accounts |

---

## 2. The `currency` → `base_currency` Rename

### Problem
hledger's `fields` directive treats certain names as **magic**. Having a field
named `currency` in the `fields` list automatically makes it a global currency
prefix for ALL amounts — equivalent to writing `currency %currency`. This broke
crypto cost notation like `0.06744992 BTC @ 59147.0 EUR` by prepending `EUR`.

### Fix
Renamed the hledger CSV column from `"currency"` to `"base_currency"` in:

- `auto_mapper.py:33` — `DEFAULT_HLEDGER_NAMES["payment_currency"]`
- `templates.py` — all 3 `("payment_currency", "...")` tuples in split groups
- `generate_rules_content.py` — all `%currency` → `%base_currency` in rules
- `GenericTransactionWithCsv.py:105` — `hledger_col_name == "base_currency"`
- `GenericTransactionWithCsv.py:137` — `result.setdefault("base_currency", ...)`
- `AccountTransaction.py:72` — `("currency", "base_currency")` mapping
- `AccountTransaction.py:128` — `hledger_col_name == "base_currency"`
- `read_csv_asset_transactions.py:73` — backward-compat: `row.get("base_currency") or row["currency"]`
- `/home/a/finance/config.yaml` — 3 saved column mappings
- Tests: `conftest.py`, `test_withdrawal_and_uncategorised.py`, `test_hledger_dict.py`

### Gotcha: `to_hledger_dict()` was hardcoding account base currency
The old code always set `result["base_currency"] = self.account.base_currency.value`
(EUR), even for sell transactions where `payment_currency` is BTC. Fixed to:
1. Read the actual `payment_currency` attribute when mapping targets `base_currency`
2. Use `result.setdefault(...)` instead of unconditional overwrite

---

## 3. Crypto Trade Rules (Buy vs Sell)

### Problem
Buy and sell transactions need fundamentally different posting structures:
- **Buy**: cost notation on the **received** crypto posting
- **Sell**: cost notation on the **source** crypto posting

hledger rules are **additive** (ALL matching blocks apply; later assignments
override, but uncleared fields persist), so a "fallback + override" pattern
doesn't work — lingering `currency1` from rule A breaks rule B.

### Solution: Mutually Exclusive Conditions

Generated in `_create_crypto_trade_rules()`:

```python
fiat = self.account_config.account.base_currency.value  # e.g. "EUR"

# Build regex matching any base_currency that is NOT the fiat code
# For EUR: ^[^E]|^E[^U]|^EU[^R]|^EUR.
not_fiat_re = ...  # computed from fiat string
```

**Buy rule** (base_currency IS fiat):
```
if %received_currency .
& %quote_price .
& %base_currency ^EUR$
 account1 assets:..:%received_currency
 amount1 %received_amount %received_currency @ %quote_price %base_currency
 account3 assets:..:%base_currency
 amount3 -%amount
 currency3 %base_currency
```

**Sell rule** (base_currency is NOT fiat):
```
if %received_currency .
& %quote_price .
& %base_currency ^[^E]|^E[^U]|^EU[^R]|^EUR.
 account1 assets:..:%received_currency
 amount1 %received_amount
 currency1 %received_currency
 account3 assets:..:%base_currency
 amount3 -%amount %base_currency @ %quote_price %received_currency
```

### How Preprocessed Data Differs by Transaction Type

| Field | Buy | Sell | Deposit | Rebate |
|-------|-----|------|---------|--------|
| `base_currency` | EUR (fiat) | BTC (crypto) | — (empty) | EUR |
| `amount` | 3999.44 (EUR spent) | 0.052 (BTC sold) | — | 0.0 |
| `received_currency` | BTC | EUR | EUR | EUR |
| `received_amount` | 0.067 | 3874.66 | 5000.0 | 10.0 |
| `quote_price` | 59147.0 | 74600.0 | — (empty) | — |

The sell group's `csv_column_mapping` swaps which raw CSV column maps to
`payment_currency` vs `received_currency`, so `base_currency` ends up as the
crypto ticker (BTC), making the regex discrimination work.

---

## 4. Other Transaction Types

### Deposits (from linked account)
Matched by `%received_currency .` AND `%quote_price ^$` (empty quote = not a trade).
Uses `linked_accounts` from config for the counterparty:
```
 account1 assets:at:bitvavo:trading:%received_currency
 amount1 %received_amount
 currency1 %received_currency
 account2 assets:at:triodos:checking
 amount2 -%received_amount
 currency2 %received_currency
```

### Rebates / Incentives
These have `received_currency=EUR`, `received_amount=10.0`, empty `quote_price`,
so they match the deposit rule. The counterparty is `assets:at:triodos:checking`
(the linked account).

### Withdrawals
Handled by `_create_withdrawal_rules()`. Domestic and foreign-currency variants.
Not exercised in current Bitvavo data.

---

## 5. Split Mode Mechanics

The Bitvavo account has 4 split groups (sell/buy/rebate/deposit), each with
different `csv_column_mapping`. Key implementation details:

- **`AccountConfig.get_hledger_csv_column_names()`** returns the **union** of
  all groups' columns (not just the first group). This ensures the `fields`
  directive in the rules file covers all possible columns.

- **`export_to_csv.py`** uses this canonical column order and fills missing
  keys with `None` via `d.setdefault(k, None)` for each dict.

- **`get_transaction_code()`** override in `GenericCsvTransaction`: for
  deposit-only rows where `tendered_amount_out=0`, it checks
  `extra["received_amount"]` to determine CREDIT/DEBIT.

---

## 6. hledger Rules Engine Gotchas

1. **Magic field names**: `currency`, `amount`, `date`, `description`, `status`
   in `fields` directive have special meaning. Never use `currency` as a
   column name — it becomes a global currency prefix.

2. **Additive rules**: ALL matching `if` blocks apply. Fields set by an earlier
   block persist even if a later block matches. Use mutually exclusive conditions.

3. **No regex lookahead**: hledger doesn't support `(?!...)` or `(?=...)`.
   Use character-class alternation: `^[^E]|^E[^U]|^EU[^R]|^EUR.` for "not EUR".

4. **`currencyN` prepends**: If both `amountN` (with embedded currency like
   `0.067 BTC @ 59147 EUR`) and `currencyN` are set, hledger prepends
   `currencyN` to `amountN`, producing `BTC0.067 BTC @ ...` (broken).

---

## 7. Config YAML Structure (Bitvavo)

```yaml
- input_csv_filename: bitvavo.csv
  base_currency: EUR
  account_holder: at
  bank: bitvavo
  account_type: trading
  decimal_format: dot
  split_column: 3          # Column index for Type (buy/sell/deposit/rebate)
  split_groups:
  - values: [sell]
    csv_column_mapping:     # 15 entries mapping raw CSV columns
    - [payment_currency, base_currency]   # col 5: Currency → base_currency
    - [negate:tendered_amount_out, amount] # col 6: Amount (negated)
    - [received_currency, received_currency]
    - [received_amount, received_amount]
    ...
  - values: [buy]
    csv_column_mapping:     # Same columns, different field assignments
    - [received_currency, received_currency] # col 5: Currency → received_currency
    - [received_amount, received_amount]     # col 6: Amount
    - [payment_currency, base_currency]      # col 9: Received/Paid Currency
    - [negate:tendered_amount_out, amount]   # col 10: Received/Paid Amount (negated)
    ...
  linked_accounts:
  - account_holder: at
    bank: triodos
    account_type: checking
    transfer_types: [deposit]
```

The `negate:` prefix on field names flips the sign during parsing (e.g.,
raw `-3999.44` becomes `+3999.44` as `tendered_amount_out`).

---

## 8. Running & Testing

### Full pipeline (preprocess + import + plot)
```bash
cd /home/a/git/git/hledger/hledger-preprocessor
source ~/miniconda3/etc/profile.d/conda.sh && conda activate hledger_preprocessor
TERM=xterm ./start.sh --config /home/a/finance/config.yaml
```

### Unit tests
```bash
python -m pytest test/unit/test_hledger_dict.py -x -q       # hledger dict generation
python -m pytest test/test_withdrawal_and_uncategorised.py -x -q  # withdrawal + edge cases
```

### Inspect generated rules
```bash
cat /home/a/finance/finance_v8/import/at/bitvavo/trading/bitvavo-trading.rules
```

### Inspect preprocessed CSV
```bash
head -5 /home/a/finance/finance_v8/import/at/bitvavo/trading/2-preprocessed/2026/bitvavo.csv
```

---

## 9. Known Limitations / Future Work

- **No auto-migration for old configs**: Existing `config.yaml` files with
  `currency` as an hledger column name need manual update to `base_currency`.
  Could add a migration step in config loading.

- **Linked account matching for deposits**: Currently deposits just use the
  first linked account as counterparty. A more sophisticated system could match
  against the linked account's transactions by date/amount.

- **Sell group assumes different fiat**: The sell regex
  `^[^E]|^E[^U]|^EU[^R]|^EUR.` is generated from the account's base currency.
  Works for any 3-letter fiat code. If someone used a 1-letter code it would
  need adjustment.

- **Receipt-based transactions**: `AccountTransaction` (for receipt-scanned
  data) also had its mapping updated but uses a separate code path. The
  internal Python dict key `"currency"` in receipt JSON is unchanged — only the
  hledger CSV column name was renamed.
