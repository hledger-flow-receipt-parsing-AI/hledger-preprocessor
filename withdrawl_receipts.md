# Fix withdrawal receipt duplicate entries

## Problem

Withdrawal receipts for `wallet:physical` (no CSV) produce `income:withdrawl` journal entries that double-count when the Triodos CSV already records the same ATM withdrawal.

**Current wallet-side entries** (4 affected):
```
2024-12-20 *
    income:withdrawl               EUR-350.00    <- WRONG
    assets:at:wallet:physical       EUR350.00    <- duplicates Triodos side

2025-02-08 *
    income:withdrawl             EUR-320.00      <- WRONG
    assets:at:wallet:physical     EUR320.00

2025-05-24 *
    income:withdrawl             EUR-220.00      <- WRONG
    assets:at:wallet:physical     EUR220.00

2025-05-15 *
    income:withdrawl               GBP-100.00   <- WRONG (foreign)
    assets:at:wallet:physical       GBP100.00
```

**Triodos already produces the correct entries** (via `private_logic.py` ATM detection → `Account(at, wallet, physical)`):
```
2024-12-20 * GELDMAAT ...
    assets:at:wallet:physical        EUR350.00
    assets:at:triodos:checking      EUR-350.00

2025-02-08 * GELDMAAT ...
    assets:at:wallet:physical        EUR320.00   (note: looking up exact date)
    assets:at:triodos:checking      EUR-320.00

2025-05-24 * GELDMAAT ...
    assets:at:wallet:physical        EUR220.00
    assets:at:triodos:checking      EUR-220.00

2025-05-15 * MFG - FOUR WANTZ FOUR ... (foreign ATM)
    expenses:withdrawl:euro:pound    EUR127.28   (note: this one goes to expenses, not wallet)
    assets:at:triodos:checking      EUR-127.28
```

## Root Cause

The wallet-side receipt transactions have `amount = -320` (negative = change_returned > tendered_amount_out for withdrawals). This matches the generic `income:` rule:
```
if %amount ^-
& %quote_price ^$
& %received_currency ^$
description %description
 account1 income:%ExampleRuleBasedModel
 account2 assets:%account_holder:%bank:%account_type
```

The `ExampleRuleBasedModel` is `"withdrawl"` (from `receipt_category`), producing `income:withdrawl`.

These receipts have **no `withdrawal_metadata`** (created before the TUI withdrawal flow existed), so the multi-posting withdrawal rules don't fire.

## Three Scenarios to Handle

### 1. Domestic withdrawal receipt (e.g. GeldMaat EUR → wallet EUR)

**Both sides record** the same transfer. The Triodos CSV produces:
```
assets:at:wallet:physical  +EUR320
assets:at:triodos:checking -EUR320
```

The wallet receipt should produce **nothing** — the Triodos side already handles it correctly. The receipt is informational (records which ATM, what denominations, etc.) but should not generate a journal entry that duplicates the bank's record.

**Solution**: When a withdrawal receipt has `withdrawal_metadata` and the source account has a CSV, the wallet side should **not generate a journal entry at all** — it should be skipped during `manage_preprocessing_assets()`.

However, hledger rules can't conditionally suppress output. The solution is to filter withdrawal transactions **before** they reach the preprocessed CSV.

### 2. Foreign withdrawal receipt (e.g. ATM in England: EUR → GBP)

The Triodos CSV records the EUR debit:
```
expenses:withdrawl:euro:pound    EUR127.28
assets:at:triodos:checking      EUR-127.28
```

The wallet receipt should record the GBP credit to the wallet. Currently it produces `income:withdrawl GBP-100 / assets:at:wallet:physical GBP100` which is wrong.

**Desired**: The wallet side should NOT produce a journal entry either. The Triodos side already debits the source. The GBP arriving in the wallet is an internal transfer — but since the Triodos side posts to `expenses:withdrawl:euro:pound` (not `assets:at:wallet:physical`), the wallet balance is wrong regardless.

**Better Triodos-side fix** (separate issue): The foreign ATM categorization in `private_logic.py` should also return `Account(at, wallet, physical)` so Triodos posts to `assets:at:wallet:physical:GBP` with currency conversion. But that's a more complex change (multi-currency posting rules needed on Triodos side).

**For now**: Skip wallet-side generation when source account has CSV, same as domestic.

### 3. Physical cash receipt (no bank involvement)

A receipt for a cash purchase (groceries, diesel) only has a `wallet:physical` AccountTransaction. There is no bank CSV involved. These should work correctly and DO work correctly today — they produce:
```
expenses:groceries:lidl          EUR29.70
assets:at:wallet:physical       EUR-29.70
```

No change needed.

### 4. Card transaction receipt (already in CSV)

A receipt for a card payment has a `triodos:checking` AccountTransaction. The matching system converts it to a `GenericCsvTransaction`, which gets filtered out by `collect_non_csv_transactions()`. The Triodos CSV handles the journal entry.

**This already works correctly.** No change needed.

## Solution: Skip withdrawal receipts when source account has CSV

### Change 1: Filter in `manage_preprocessing_assets()`

**File**: `src/hledger_preprocessor/management/main_manager.py`, lines 144-179

Before classifying and adding a receipt's AccountTransaction to the preprocessed CSV, check if the receipt is a withdrawal AND the source account (from `withdrawal_metadata`) has its own CSV. If so, skip the wallet-side transaction entirely.

```python
for receipt_account_transaction in all_account_transactions:
    for account_config in config.get_account_configs_without_csv():
        if receipt_account_transaction.account == account_config.account:

            # NEW: Skip withdrawal transactions when source has CSV
            if _should_skip_withdrawal_transaction(
                receipt=labelled_receipt,
                config=config,
            ):
                continue

            # ... existing classify + append logic ...
```

```python
def _should_skip_withdrawal_transaction(
    *, receipt: Receipt, config: Config
) -> bool:
    """Skip wallet-side withdrawal entry when the source bank already
    imports via CSV (Triodos side handles the full journal entry)."""
    if receipt.withdrawal_metadata is None:
        return False
    source = receipt.withdrawal_metadata.source_account_transaction.account
    return any(
        ac.account.account_holder == source.account_holder
        and ac.account.bank == source.bank
        and ac.account.account_type == source.account_type
        and ac.has_input_csv()
        for ac in config.accounts
    )
```

### Change 2: No rule changes needed

The withdrawal rules (`_create_withdrawal_rules`) stay as-is. They're only useful for the rare case where a wallet withdrawal's source account does NOT have a CSV (e.g., borrowing cash from someone). In that case, the multi-posting entry is needed and correct.

### What about receipts WITHOUT `withdrawal_metadata`?

The 4 existing problem receipts have `withdrawal_metadata = None`. The filter in Change 1 won't help them — they'll still produce `income:withdrawl` entries.

**These receipts need to be re-labelled through the TUI** to set their `withdrawal_metadata`. Once re-labelled:
- The TUI withdrawal flow sets `withdrawal_metadata.source_account_transaction.account` to `at:triodos:checking`
- `_should_skip_withdrawal_transaction` returns `True`
- The wallet-side entry is suppressed
- The Triodos CSV handles the journal entry

## Does the TUI already support this?

**Yes.** The `WithdrawalQuestions` TUI flow:
1. Asks for ATM operator fee
2. Asks for source account (e.g., `at:triodos:checking`)
3. Asks for source currency
4. Asks for conversion method (amount or exchange rate)
5. Pre-fills amount via background CSV matching

This produces a complete `WithdrawalMetadata` object. The TUI is ready — it just wasn't used for these 12 receipts (created before the flow existed).

## Action Items

### Code change (1 file)
1. Add `_should_skip_withdrawal_transaction()` helper to `main_manager.py`
2. Call it in `manage_preprocessing_assets()` before classify+append

### Manual re-labelling (user action)
Re-label the 4 wallet-side withdrawal receipts through the TUI. The remaining 8 withdrawal receipts only have `triodos:checking` transactions (filtered out already by `collect_non_csv_transactions` since triodos has a CSV + the matching converts them to `GenericCsvTransaction`).

The 4 receipts to re-label are the ones whose wallet:physical preprocessed CSV entries have `"withdrawl"` as description:
- 2024-12-20 EUR 350 withdrawal
- 2025-02-08 EUR 320 withdrawal
- 2025-05-15 GBP 100 withdrawal (foreign, Cashzone Ongar)
- 2025-05-24 EUR 220 withdrawal

## Verification

After code change + re-labelling:
1. Run the preprocessor: no `income:withdrawl` entries in `at/wallet/physical/3-journal/`
2. Triodos journals still show correct `assets:at:wallet:physical` entries for domestic withdrawals
3. `hledger bal assets:at:wallet:physical` shows correct balance (no double-counting)
4. Physical cash receipts (groceries etc.) still produce correct expense entries
