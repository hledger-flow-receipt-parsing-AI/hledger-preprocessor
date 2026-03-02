# Fix v9.D — Fill the WHOLE receipt in the demo GIF

## Context

The receipt editing demo GIF is driven by simulated keypresses in:

```
gifs/automation/receipt_editor.py  →  function run_edit_receipt_demo()  (lines 119–193)
```

This file uses `TuiNavigator` (pexpect wrapper in `gifs/automation/tui_navigator.py`)
to spawn the real `hledger_preprocessor --edit-receipt` TUI and send keystrokes.

The GIF is recorded by `gifs/2b_label_receipt/generate.sh` which calls
`run_full_pipeline "gifs.automation.receipt_editor"`, records via asciinema,
then converts to themed GIFs + MP4.

## Current behaviour (broken)

The demo edits the `repairs:bike` receipt fixture. It currently:

1. Selects the receipt from the list (↓ + Enter)
2. Answers "Can you see" prompt (Enter)
3. Skips the date field (Enter — keeps existing value)
4. Deletes the old category `repairs:bike` and types `groceries:ekoplaza`
5. **Arrows through all remaining fields without changing them** (15× ↓)
6. Confirms "Done with receipt" (Enter)

This means the GIF only shows the category being changed. All other fields
(account, currency, amount, change, shop address, subtotal, tax) are just
scrolled past.

## Required behaviour (v9.D)

The demo should **fill in every field** of the receipt, not just change the
category. The viewer should see each field being actively filled in so they
understand what data the TUI collects.

## TUI field sequence (in order)

The receipt TUI fields appear in this order after the "Can you see" prompt:

| # | Field | Type | repairs_bike.json value | Target value for demo |
|---|-------|------|------------------------|-----------------------|
| 1 | Receipt date and time | DateTime text input | `2025-06-15T14:30:00` | `2025-01-15T10:30:00` |
| 2 | Bookkeeping expense category | Text input | `repairs:bike` | `groceries:ekoplaza` |
| 3 | Account (bank/wallet) | Vertical multiple choice | `at:wallet:physical` (index 1) | `at:triodos:checking` (index 0) |
| 4 | Currency | Vertical multiple choice | `EUR` | `EUR` (keep) |
| 5 | Amount paid | Float input | `20.0` | `42.17` |
| 6 | Change returned | Float input | `5.5` | `0` |
| 7 | Add another account? | Horizontal choice (y/n) | `n` | `n` (keep) |
| 8 | Select Shop Address | Vertical multiple choice | `BikeShop` | Select `Ekoplaza` or enter new |
| 9 | Subtotal (optional) | Float input | (empty) | (skip — Enter) |
| 10 | Total tax (optional) | Float input | `2.55` | `7.35` |
| 11 | Done with this receipt? | Horizontal choice | `yes` | `yes` |

## What to change

Edit **only** `gifs/automation/receipt_editor.py`, function `run_edit_receipt_demo()`,
lines 119–193. Replace the current keypress sequence with one that fills every field.

### Key things to know

- `TuiNavigator` API (defined in `gifs/automation/tui_navigator.py`):
  - `nav.press_enter()` — confirm/advance
  - `nav.press_down(times=N)` — navigate down in selection lists
  - `nav.press_up(times=N)` — navigate up
  - `nav.press_backspace(times=N)` — delete characters
  - `nav.type_text("text", char_pause=0.1)` — type character by character (visible in GIF)
  - `nav.send(Keys.END)` — move cursor to end of field
  - `nav.send(Keys.HOME)` — move cursor to start of field
  - `nav.wait_for("pattern", timeout=N, silent=True)` — wait for text to appear
  - `nav.flush_output()` — flush pexpect buffer

- For **text input fields** (date, category, amount, etc.): the field is pre-filled
  with the existing value. You need to: `Keys.END` → backspace to clear → type new value → `Enter`/`↓` to advance.

- For **vertical multiple choice fields** (account, currency, shop address):
  use `↓`/`↑` to move highlight, `Enter` to select.

- For **horizontal multiple choice fields** (add another account, done):
  the first option is already highlighted; just press `Enter` to confirm.

- Add `time.sleep()` pauses between fields so the viewer can see what's happening.
  Use ~0.3–0.5s between actions, ~0.8–1.0s after typing a full value.

- The `show_before_state()` and `show_after_state()` calls before/after the TUI
  should remain — they show the JSON diff. But update `show_after_state` to use
  a more comprehensive jq field (e.g., `.` or `.net_bought_items`) instead of
  just `.receipt_category`.

### Testing

The demo edits whichever receipt matches `source_category="repairs:bike"`.
The test fixture is seeded by `test/conftest.py` via
`test/fixtures/receipts/repairs_bike.json`.

After making changes:

```bash
# Regenerate the receipt GIF (records + stitches full-path):
conda run -n hledger_preprocessor python -m pytest test/e2e/test_gif_2b_label_receipt.py -xvs

# Rebuild and serve the site:
./build_userstories.sh --site --serve
```

Open `http://localhost:8059/stories/US-2b.1.html` to verify the GIF shows
all fields being filled in.

### Important constraints

- Do NOT change any other files (tui_navigator.py, generate.sh, etc.)
- Do NOT change the test fixture JSON files
- Do NOT change the layout or structure of the site
- Keep the same overall flow: before state → command → TUI → after state
- The function signature and parameters should stay the same
