# Fix: Foreign Currency Matching GIF Hangs During Automated Recording

## Before You Start

Read these files for project conventions and context:
- `gifs/CLAUDE.md` — GIF directory structure and overview
- `~/.claude/projects/-home-a-git-git-hledger/memory/MEMORY.md` — debugging patterns (especially shell double-quote escaping in `python3 -c "..."` blocks, and the requirement to always end userstory work with rebuild/serve commands)

## Problem

Running `./build_userstories.sh --gifs` hangs on the `3b_foreign_currency_match` GIF.
The automation gets stuck at an interactive "No matches found" prompt that it doesn't handle.

## Reproduction

```bash
cd /home/a/git/git/hledger/hledger-preprocessor
source ~/miniconda3/etc/profile.d/conda.sh && conda activate hledger_preprocessor
python -m gifs.automation.setup_test_environment
./build_userstories.sh --gifs --config /tmp/hledger_demo/config.yaml
```

It hangs after printing:

```
No matches found for the above transaction in a receipt of:
    2025-03-20 14:00:00
from account:
    at:triodos:checking.
Please select an action (enter a number 1-5):

1. Add estimated conversion rate for alternative currency.
2. Check if the receipt is correct
3. Check if transactions for this account are up to date
4. Widen the date margin
5. Widen the amount margin
```

## Root Cause

**File:** `gifs/automation/real_foreign_currency_match_demo.py` (lines 354-374)

The `run_matching_demo()` function uses pexpect to wait for patterns, but only handles:
- `"ignore_keys="` — debug prompt from matching algorithm
- `"EXPORTING to:"` — confirmation prompt before saving

It does NOT handle the "No matches found → Please select an action" prompt.

**Why no matches are found:** The test data creates:
- A receipt in GBP (100.00 GBP ATM withdrawal)
- A CSV transaction in EUR (117.50 EUR from Barclays ATM London)

The matching algorithm searches for "EUR 100.00" but the CSV has "117.50 EUR" (= 100 GBP × 1.175 conversion rate). Without the conversion rate pre-configured, matching fails and prompts the user.

## Key Files

| File | Role |
|------|------|
| `gifs/3b_foreign_currency_match/generate.sh` | GIF build script — runs asciinema recording |
| `gifs/automation/real_foreign_currency_match_demo.py` | Automation script driving the demo (lines 59-257: test data setup, lines 312-394: pexpect interaction — **the bug**) |
| `gifs/automation/tui_navigator.py` | Pexpect-based helper (`wait_for`, `press_enter`, `send`) |
| `src/hledger_preprocessor/matching/ask_user_action.py` | The interactive prompt handler (lines 228-265) — loops until valid 1-6 input |
| `build_userstories.sh` | Build orchestration — `3b_foreign_currency_match` is in the standalone GIFs array (line ~268) |

## What the Fix Needs to Do

The automation in `real_foreign_currency_match_demo.py` `run_matching_demo()` must:

1. **Detect** the "Please select an action" or "No matches found" prompt via pexpect
2. **Send "1"** (Add estimated conversion rate for alternative currency)
3. **Then handle** the follow-up prompt for the conversion rate value by **sending "1.175"**
4. After providing the conversion rate, the matching should succeed and proceed to the existing `"EXPORTING to:"` handler

### Implementation approach

Add a new pattern to the `nav.child.expect()` call:

```python
index = nav.child.expect(
    [
        "ignore_keys=",
        "EXPORTING to:",
        "Please select an action",   # <-- NEW: handle no-match prompt
        pexpect.EOF,
        pexpect.TIMEOUT,
    ],
    timeout=30,
)
```

Then handle index 2 by:
- Sending "1\n" to select "Add estimated conversion rate"
- Waiting for the conversion rate input prompt
- Sending "1.175\n"
- Looping back to wait for the next prompt

### Important context

- Check `ask_user_action.py` to see the exact prompts and expected input format after selecting option 1
- The conversion rate 1.175 = 117.50 EUR / 100.00 GBP
- Other automation scripts have the same incomplete pattern — `real_link_receipts_demo.py`, `real_widen_date_demo.py`, `real_disambiguate_demo.py` may need similar fixes
- The conda environment is `hledger_preprocessor` (Python 3.12)

## Environment Setup

```bash
# Activate conda env
source ~/miniconda3/etc/profile.d/conda.sh && conda activate hledger_preprocessor

# Set up test data
python -m gifs.automation.setup_test_environment

# Test just the foreign currency GIF
./build_userstories.sh --gif 3b_foreign_currency_match --config /tmp/hledger_demo/config.yaml

# Test all GIFs
./build_userstories.sh --gifs --config /tmp/hledger_demo/config.yaml --serve
```

## Verification

After fixing, the full `--gifs` build should complete without hanging, and the `3b_foreign_currency_match` GIF should show:
1. The receipt and CSV data displayed
2. The "No matches found" prompt appearing
3. Option 1 selected (add conversion rate)
4. Conversion rate 1.175 entered
5. Successful match and export
