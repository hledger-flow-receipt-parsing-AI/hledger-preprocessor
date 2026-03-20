# Plan: Clean up withdrawal account structure

## Problem

ATM withdrawals produce `assets:at:wallet:physical:withdrawl` — mixing location with action. The `:withdrawl` suffix is hardcoded in `rule_based_eg0.py:46` for every `Account` return, creating a sub-account that doesn't represent a real entity.

## Current flow

1. `private_logic.py` detects ATM (GeldMaat, etc.) → returns `Account(at, wallet, physical)`
2. `rule_based_eg0.py:46` appends `:withdrawl` → CSV gets `at:wallet:physical:withdrawl`
3. `generate_rules_content.py:99` matches this with `& %ExampleRuleBasedModel at:wallet:physical` → posts to `assets:at:wallet:physical:withdrawl`

## Target

Withdrawals post directly to `assets:at:wallet:physical` — no `:withdrawl` suffix.

## Changes

### 1. `rule_based_eg0.py` — remove `:withdrawl` suffix
**Line 44-47**: Change Account handling from:
```python
if isinstance(classification, Account):
    return f"{classification.to_string()}:withdrawl"
```
to:
```python
if isinstance(classification, Account):
    return classification.to_string()
```

### 2. `generate_rules_content.py` — update no-CSV account rules
**Lines 93-104 (expense) and 132-143 (income)**: The rules currently match `%ExampleRuleBasedModel at:wallet:physical` and post to `assets:%ExampleRuleBasedModel`. Without the `:withdrawl` suffix, `%ExampleRuleBasedModel` = `at:wallet:physical`, so `assets:%ExampleRuleBasedModel` = `assets:at:wallet:physical`. This already works — no change needed.

### 3. `categories.yaml` — remove stale entries
Remove `wallet: physical: {}` if no longer used as a category (it was only reachable via the Account return path, not as a Category).

Keep `withdrawl: euro: pound: {}` if the foreign-currency withdrawal TUI flow still returns it as a Category.

### 4. `private_logic.py` — no changes needed
The 4 ATM detection blocks (GeldMaat, Société Générale, Portugal, Oldenzaal) already return `Account` objects. They'll just produce `at:wallet:physical` instead of `at:wallet:physical:withdrawl`.

### 5. Bitvavo Account return — verify no breakage
Line 289-297 returns `Account(at, bitvavo, trading)`. Currently produces `at:bitvavo:trading:withdrawl`. After this change it produces `at:bitvavo:trading`. The clearing account rules at lines 108-119 match `%ExampleRuleBasedModel at:bitvavo:trading` — still works.

### 6. Fix existing journal data
Run a one-time rename to merge the old `:withdrawl` sub-account into the parent:
```bash
hledger -f all-years.journal print | sed 's/assets:at:wallet:physical:withdrawl/assets:at:wallet:physical/g' > fixed.journal
```
Or add an alias in the journal: `alias assets:at:wallet:physical:withdrawl = assets:at:wallet:physical`

## Files touched
| File | Change |
|------|--------|
| `src/.../rule_based/rule_based_eg0.py` | Remove `:withdrawl` suffix (1 line) |
| `/home/a/finance/categories.yaml` | Remove `wallet: physical: {}` if unused |
| Journal files | One-time rename or alias |

## Tests to update
- `test_withdrawal_tui_and_journal.py` — any assertions expecting `:withdrawl` suffix in classification strings
