# Handover: CSV Mapping TUI (Issue #15)
You are a world class developer, with decades of work on tui implementations, you are driven to perfection and have an IQ of 160.
## Project
- **Root**: `/home/a/git/git/hledger/hledger-preprocessor`
- **Conda env**: `hledger_preprocessor` (Python 3.12)
- **Entry point**: `hledger_preprocessor --map-csv <csv_file> --config <config.yaml>`
- **Tests**: `python -m pytest test/ -v` (311 tests as of last count)

## What exists

A standalone terminal TUI (`mapping_tui.py`) for mapping CSV columns to hledger transaction fields. No urwid — raw `termios`/`tty` with ANSI escape codes. Split-pane layout: scrollable CSV table top, questions bottom.

### Features implemented (this session + previous)

1. **Split-by-Type** — A single CSV with mixed row types (e.g. Bitvavo: deposit, buy, sell, rebate) can be split by a type column. Each group of row types gets its own column mapping, all stored in one `AccountConfig`.

2. **Exchange rate / quote price toggle** — Mutual exclusivity: picking `exchange_rate` grays out `quote_price` and vice versa.

3. **Template-based mapping** — Auto-detects CSV format from headers (Bitvavo template exists). If detected, user can accept the template to skip manual mapping.

4. **Two-pass preview** — After mapping, parsed sample rows are displayed for verification before saving.

5. **Pre-fill across groups** — When mapping subsequent split groups, the previous group's choices are pre-filled as defaults. Uses a `_NO_PREV` sentinel to distinguish "no previous group" from "previous group chose Skip".

6. **Go-back navigation (IN PROGRESS — HAS A BUG)** — Press Escape at any question to go back to the previous step. Uses a `GoBack` exception + step-based loop in `run_csv_mapping_tui()`.

## Architecture

### Key files

| File | Purpose |
|------|---------|
| `src/hledger_preprocessor/csv_mapping/mapping_tui.py` | Main TUI — all rendering, input, step loop, column mapping |
| `src/hledger_preprocessor/csv_mapping/templates.py` | Template definitions (Bitvavo) + `detect_template()` |
| `src/hledger_preprocessor/csv_mapping/auto_mapper.py` | Auto-maps CSV headers to field names by fuzzy matching |
| `src/hledger_preprocessor/csv_mapping/csv_reader.py` | `read_csv_preview()` — reads headers + sample rows |
| `src/hledger_preprocessor/config/AccountConfig.py` | `AccountConfig` + `SplitGroup` dataclasses, `parse_csv_rows()` |
| `src/hledger_preprocessor/config/Config.py` | YAML parsing for split_column, split_groups, decimal_format |
| `src/hledger_preprocessor/generics/parse_generic_tnx_with_csv.py` | Decimal-format-aware CSV row parsing |
| `src/hledger_preprocessor/__main__.py` | CLI entry point, calls `run_csv_mapping_tui()` |
| `src/hledger_preprocessor/csv_mapping/csv_mapping_tui.md` | Design doc for features 1+5+6+7 |

### Data model

```python
@dataclass(frozen=True)
class SplitGroup:
    values: Tuple[str, ...]           # e.g. ("buy", "sell")
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
```

**Key constraint**: One CSV → one `AccountConfig`. No changes to downstream code (`csv_to_transactions.py` etc). The split logic lives entirely in `AccountConfig.parse_csv_rows()`.

### TUI step loop (`run_csv_mapping_tui`)

The main flow is a `while step < len(_STEPS)` loop with these steps:

| # | Name | What runs |
|---|------|-----------|
| 0 | `account_holder` | `ask_string` |
| 1 | `bank` | `ask_string` |
| 2 | `account_type` | `ask_string` |
| 3 | `base_currency` | `ask_currency` |
| 4 | `mapping` | `_run_mapping_step()` — template detection + split decision + column mapping |
| 5 | `decimal_format` | `_run_decimal_step()` — auto-detect or ask |
| 6 | `preview` | `_run_preview_step()` — show parsed rows, confirm |
| 7 | `summary` | `_run_summary_step()` — show summary, confirm save |

State is stored in a `state: Dict[str, Any]`. A `log_snapshots: List[int]` tracks `len(answer_log)` at each step's start for rollback on `GoBack`.

### Go-back mechanism

- `GoBack(Exception)` — raised when user presses Escape
- Bare Escape detected via `select.select()` with 50ms timeout in `_read_key_raw()` (distinguishes `\x1b` alone from `\x1b[A` arrow sequences)
- Each `ask_*` method (`ask_string`, `ask_confirm`, `ask_choice`, `ask_column_select`) has `elif key == "esc": raise GoBack`
- `ask_currency` wraps `ask_string`, so `GoBack` propagates naturally
- `_run_column_mapping` uses a `while col_idx` loop: Escape at col N goes back to col N-1; at col 0 propagates `GoBack` to the step loop
- Group collection (Phase 1) and group mapping (Phase 2) have similar per-item back-navigation
- `interactive_steps: Dict[int, bool]` tracks which steps asked user a question; non-interactive steps are skipped when going back

### TUI class: `_SplitPaneTUI`

Key state:
- `answer_log: List[str]` — completed answers, shown dimmed in bottom pane
- `bottom_lines: List[str]` — current question content in bottom pane
- `highlight_col: int` — highlighted column in CSV table (-1 = none)
- `choice_active`, `input_active` — which input mode is active
- `col_offset`, `row_offset` — table scroll state

Key methods:
- `ask_string(prompt, default)` → `str`
- `ask_confirm(prompt)` → `bool`
- `ask_choice(col_idx, auto, used, chosen, default_field, use_auto_default)` → `int` (index into `FIELD_CHOICES`)
- `ask_column_select(prompt)` → `int` (column index)
- `ask_currency()` → `Currency`
- `draw()` — full screen redraw
- `_redraw_bottom_only()` — partial redraw (less flicker)

## CURRENT BUG: Go-back from preview loops infinitely

### Problem
When the user rejects the preview (answers "n" to "Does the preview look correct?") or presses Escape, the TUI stays on the same screen instead of going back.

### Root cause
The step loop on `GoBack` decrements the step from 6 (preview) to 5 (decimal_format). But `_run_decimal_step()` auto-detects the format without asking any question, so it completes instantly and advances back to step 6 (preview) — creating an infinite loop.

The `interactive_steps` skip-back mechanism was added to handle this: non-interactive steps should be skipped when going back. However, the check `interactive_steps.get(step, True)` defaults to `True` (interactive) for steps not yet recorded. The decimal_format step sets `state["_decimal_was_asked"] = False` when auto-detected, and the step loop reads it:

```python
interactive_steps[step] = True
if current == "decimal_format":
    interactive_steps[step] = state.get("_decimal_was_asked", False)
```

The skip-back logic:
```python
except GoBack:
    if step > 0:
        step -= 1
        while step > 0 and not interactive_steps.get(step, True):
            step -= 1
```

**The bug**: When preview raises `GoBack`, `step` becomes 5 (decimal_format). `interactive_steps[5]` was set to `False` (auto-detected). The while loop then decrements to step 4 (mapping), which IS interactive. So it should stop at step 4. **BUT** — on re-entering step 4, the mapping step clears `decimal_format` from state:

```python
elif current == "mapping":
    for k in ("template_applied", "split_column", "split_groups_data", "chosen", "decimal_format"):
        state.pop(k, None)
```

This means the user has to redo the entire mapping from scratch (template detection, split decision, all column mappings) just because they rejected the preview. That's not a loop bug — it's a UX problem where going back from preview forces too much re-work.

### Possible fixes

**Option A**: Don't clear `decimal_format` when re-entering the mapping step. Only clear mapping-specific state. This way, going back from preview → skips decimal_format → lands on mapping, but the mapping itself is the heavy step (all column choices).

**Option B**: Make the preview step go back to a more granular target. Instead of the step loop, the preview rejection could re-enter just the last group's column mapping, or offer a choice of what to re-do.

**Option C**: When preview is rejected, instead of `raise GoBack`, show a sub-menu: "What would you like to change? [1] Column mapping [2] Decimal format [3] Start over" — then jump to the appropriate step directly by setting `step = N`.

**Option D**: Make the back-skip smarter — when the target step (mapping) would force re-doing everything, instead just don't go back that far. Stop at decimal_format even if it was auto-detected, but this time force it to ask the user (make it interactive on re-entry).

### What needs testing
Do not run the whole test kit, only run tests specificially for this csv mapping tui if you need to run any tests at all.

## Other pending item from csv_mapping_tui.md

The user added a note:
> ensure the user can negate a column. from -5 to 5 or vice versa.

This means adding a "negate" modifier to numeric field mappings so that e.g. a column with `-5000` can be stored as `5000` (or vice versa). This has NOT been implemented yet.

## Key debugging patterns (from MEMORY.md)

- **Regex escaping in .cast files**: `.cast` JSON uses `\\r`. In Python raw strings: `r'\\r'` matches 1 backslash + r. `r'\\\\r'` would match 2 backslashes + r (wrong).
- **Shell double-quote escaping**: `generate.sh` embeds Python in `python3 -c "..."`. Any `"` in Python code (even comments) terminates the shell string. Use `'` inside.
- **InputValidationQuestion.set_answer()**: For `InputType.FLOAT`, pass `float`/`int`, NOT a string.
- **TUI corruption**: Never emit text to stdout while urwid owns the screen (not relevant here since this TUI uses raw termios, not urwid).

## Build / run commands

**Full pipeline (re-record GIF + rebuild website + serve)**:
```bash
source ~/miniconda3/etc/profile.d/conda.sh && conda activate hledger_preprocessor && python -m gifs.automation.setup_test_environment && ./build_userstories.sh --gif 2b_label_receipt --config /tmp/hledger_demo/config.yaml
```

**Run the CSV mapping TUI on Bitvavo CSV**:
```bash
source ~/miniconda3/etc/profile.d/conda.sh && conda activate hledger_preprocessor && hledger_preprocessor --map-csv /home/a/finance/bitfavo.csv --config /tmp/hledger_demo/config.yaml
```

**Run tests**:
```bash
source ~/miniconda3/etc/profile.d/conda.sh && conda activate hledger_preprocessor && python -m pytest test/ -v
```

## Summary of what to do next

1. **Fix the go-back-from-preview bug** — Choose one of Options A-D above (or a better approach). The core issue: going back from preview should let the user tweak something without redoing everything.
2. **Run the test suite** — 311 tests, none have been run since the go-back refactor.
3. **Implement column negation** — Allow the user to mark a numeric column as negated (multiply by -1 during parsing). The user noted this in `csv_mapping_tui.md`.
