# Handover: Withdrawal Fee Changes

## Goal

Change the withdrawal flow so that:
1. **Two fee questions are always asked** (not just for foreign): an ATM/destination-side fee and a bank/source-side fee.
2. The fees are **included in** (not on top of) the source and destination amounts — i.e. the user enters the total amount debited from source and the total amount returned to destination, and the fees explain how those totals break down.
3. For **domestic** (same-currency) withdrawals: validate that the 4 values balance: `amount_debited = change_returned + atm_fee + bank_fee`. Highlight red if they don't.
4. **Always include non-zero fee postings** in the hledger journal rules (domestic AND foreign).

## Concrete example (domestic)

User withdrew cash at an ATM. Bank statement shows 330 EUR debited. ATM receipt says 320 EUR dispensed. The ATM charged 5 EUR, the bank charged 5 EUR.

TUI answers:
- Amount debited from source account: **330** (total out of bank)
- Change returned to account: **320** (cash received into wallet)
- ATM operator fee: **5** (charged by ATM, in destination currency)
- Bank fee: **5** (charged by source bank, in source currency)

Balance check: `330 == 320 + 5 + 5` ✓

hledger journal:
```
2025-03-30 ATM Withdrawal
    assets:at:wallet:physical        320.00 EUR  ; cash received
    expenses:atm:operator-fee          5.00 EUR  ; ATM fee
    expenses:fees:bank                 5.00 EUR  ; bank fee
    assets:at:triodos:checking      -330.00 EUR  ; total debited
```

## Concrete example (foreign)

User withdrew GBP from a EUR account. Bank debited 130 EUR. ATM dispensed 100 GBP but charged 3 GBP fee. Bank charged 2 EUR fee. Exchange rate 1 EUR = 0.8 GBP.

TUI answers:
- Amount debited from source account: **130** EUR
- Change returned to account: **100** GBP (what went into wallet)
- ATM operator fee: **3** GBP (in destination/withdrawn currency)
- Bank fee: **2** EUR (in source currency)
- Exchange rate: **0.8** (1 EUR = 0.8 GBP)

hledger journal:
```
2025-03-30 ATM Withdrawal (foreign currency)
    assets:at:wallet:physical        100.00 GBP  ; cash received
    expenses:atm:operator-fee          3.00 GBP  ; ATM fee (dest currency)
    expenses:fees:bank                 2.00 EUR  ; bank fee (source currency)
    assets:at:triodos:checking      -130.00 EUR  ; total debited
```

## Current state of code

### TUI question flow (when withdrawal toggle = "y")

**Base withdrawal questions** (injected after toggle, before wallet account):
1. "Withdrawal source account:" (VerticalMultipleChoice)
2. "Source account currency:" (VerticalMultipleChoice)
3. "Amount debited from source account:" (FLOAT)

**Wallet account questions** (standard, minus "Amount paid from account:" which is hidden):
4. "Belongs to bank/accounts_without_csv:" (VerticalMultipleChoice)
5. "Currency:" (VerticalMultipleChoice)
6. "Change returned to account:" (FLOAT)
7. "Add another account (y/n)?" (HorizontalMultipleChoice)

**Post-account questions** (injected after "Add another account = n"):
8. "ATM operator fee (in withdrawn currency, 0 if none):" (FLOAT, default "0") — **always**
9. "Exchange rate (1 source = X destination):" (FLOAT, default "1") — **foreign only**
10. "Bank fee (in source currency, 0 if none):" (FLOAT, default "0") — **foreign only**

### Key files

| File | What it does |
|------|-------------|
| `tui-image-labeller/src/tui_labeller/tuis/urwid/receipts/WithdrawalQuestions.py` | Defines all withdrawal question data objects |
| `tui-image-labeller/src/tui_labeller/tuis/urwid/question_app/reconfiguration/reconfiguration.py` | `handle_post_account_withdrawal_questions()` — injects post-account questions; `handle_withdrawal_toggle()` — injects/removes base withdrawal questions; `_prefill_withdrawal_from_metadata()` — prefills answers when editing |
| `tui-image-labeller/src/tui_labeller/tuis/urwid/receipts/account_parser.py` | `parse_withdrawal_answers()` — reads TUI answers → `WithdrawalMetadata` |
| `tui-image-labeller/src/tui_labeller/tuis/urwid/receipts/create_receipt.py` | `build_receipt_from_answers()` — calls `parse_withdrawal_answers` and builds `Receipt` |
| `hledger-preprocessor/src/hledger_preprocessor/TransactionObjects/Receipt.py` | `WithdrawalMetadata` dataclass (line 33) |
| `hledger-preprocessor/src/hledger_preprocessor/TransactionObjects/ProcessedTransaction.py` | `to_hledger_dict()` — maps `WithdrawalMetadata` → CSV columns |
| `hledger-preprocessor/src/hledger_preprocessor/rules/generate_rules_content.py` | `_create_withdrawal_rules()` — generates hledger rules that turn CSV columns into journal postings |
| `hledger-preprocessor/test/test_withdrawal_tui_and_journal.py` | All withdrawal tests |

### CSV columns (populated by `to_hledger_dict()`)

| Column | Source | Notes |
|--------|--------|-------|
| `withdrawal_source_account` | `wm.source_account_transaction.account` | e.g. `at:triodos:checking` |
| `withdrawal_source_amount` | `wm.source_account_transaction.tendered_amount_out` | Total debited from source |
| `withdrawal_source_currency` | `wm.source_account_transaction.account.base_currency` | e.g. `EUR` |
| `withdrawal_atm_fee` | `wm.atm_operator_fee` | Always populated (default 0.0) |
| `withdrawal_dest_amount` | `wm.withdrawn_amount` | Non-empty only for foreign (triggers foreign rule) |
| `withdrawal_exchange_rate` | `wm.exchange_rate` | Empty for domestic |
| `withdrawal_bank_fx_fee` | `wm.bank_fx_fee` | Currently empty string for domestic, value for foreign |

### Current hledger rules

**Domestic** (`withdrawal_dest_amount` is empty):
```
if %withdrawal_source_account .
& %withdrawal_dest_amount ^$
description ATM Withdrawal
 account1 assets:%account_holder:%bank:%account_type
 amount1 %amount
 currency1 %base_currency
 account2 assets:%withdrawal_source_account
 currency2 %base_currency
```
Only 2 postings. No fee postings. `%amount` = receipt-side amount from wallet CSV row.

**Foreign** (`withdrawal_dest_amount` is non-empty):
```
if %withdrawal_source_account .
& %withdrawal_dest_amount .
description ATM Withdrawal (foreign currency)
 account1 assets:%account_holder:%bank:%account_type
 amount1 %withdrawal_dest_amount
 currency1 %base_currency
 account2 expenses:atm:operator-fee
 amount2 %withdrawal_atm_fee
 currency2 %base_currency
 account3 assets:%withdrawal_source_account
 amount3 -%withdrawal_source_amount
 currency3 %withdrawal_source_currency
```
3 postings. ATM fee only. **Bank fee is declared in `WITHDRAWAL_FIELDS` but never used in any rule posting** — this is a bug.

### Important patterns from MEMORY.md

- `InputType.FLOAT` `set_answer()` expects `float`/`int`, NOT a string
- hledger zero-amount postings (e.g. `0.00 EUR`) are silently omitted from reports — so always including fee postings is safe
- The `reconfigurer=True` flag on a question causes a TUI pause + `get_configuration()` call when the user answers it

## Changes needed

### 1. `reconfiguration.py` — `handle_post_account_withdrawal_questions()`

**Always inject bank fee** (not just for foreign).

Current (line 606-610):
```python
post_questions = [withdrawal_questions.get_atm_fee_question()]
if is_foreign:
    post_questions.append(withdrawal_questions.get_exchange_rate_question())
    post_questions.append(withdrawal_questions.get_bank_fee_question())
```

Change to:
```python
post_questions = [
    withdrawal_questions.get_atm_fee_question(),
    withdrawal_questions.get_bank_fee_question(),
]
if is_foreign:
    post_questions.append(withdrawal_questions.get_exchange_rate_question())
```

New question order: ATM fee → Bank fee → (Exchange rate if foreign).

**Add domestic balance validation** after `set_default_focus_and_answers`:
- If not foreign, read all 4 values via `_get_tui_answer`: `amount_debited`, `change_returned`, `atm_fee`, `bank_fee`
- Check: `round(amount_debited, 2) == round(change_returned + atm_fee + bank_fee, 2)`
- If imbalanced: find the bank fee `AttrMap` wrapper and call `inp.set_attr_map({None: "error"})` to highlight red
- If balanced: ensure it's `inp.set_attr_map({None: "normal"})`

The bank fee question string is `"Bank fee (in source currency, 0 if none):"`.

### 2. `generate_rules_content.py` — `_create_withdrawal_rules()`

**Domestic rule** — add fee postings (4 postings):
```
if %withdrawal_source_account .
& %withdrawal_dest_amount ^$
description ATM Withdrawal
 account1 assets:%account_holder:%bank:%account_type
 amount1 %amount
 currency1 %base_currency
 account2 expenses:atm:operator-fee
 amount2 %withdrawal_atm_fee
 currency2 %base_currency
 account3 expenses:fees:bank
 amount3 %withdrawal_bank_fx_fee
 currency3 %base_currency
 account4 assets:%withdrawal_source_account
 currency4 %base_currency
```

Both fee currencies are `%base_currency` for domestic (same currency).

hledger silently ignores zero-amount postings, so `0.0 EUR` fee postings won't appear in reports.

Note: `%amount` comes from the receipt account transaction's net amount (change_returned - tendered_amount_out = change_returned for withdrawals). The source-side amount is auto-inferred by hledger since all other postings have explicit amounts (the balancing posting = -(change_returned + atm_fee + bank_fee) = -amount_debited).

Actually, **`account4` doesn't specify an amount** — hledger infers it as the balancing amount. This is correct because `amount_debited = change_returned + atm_fee + bank_fee` (enforced by the TUI validation). If fees are 0, the balance is just `-change_returned`.

**Foreign rule** — add bank fee posting (4 postings):
```
if %withdrawal_source_account .
& %withdrawal_dest_amount .
description ATM Withdrawal (foreign currency)
 account1 assets:%account_holder:%bank:%account_type
 amount1 %withdrawal_dest_amount
 currency1 %base_currency
 account2 expenses:atm:operator-fee
 amount2 %withdrawal_atm_fee
 currency2 %base_currency
 account3 expenses:fees:bank
 amount3 %withdrawal_bank_fx_fee
 currency3 %withdrawal_source_currency
 account4 assets:%withdrawal_source_account
 amount4 -%withdrawal_source_amount
 currency4 %withdrawal_source_currency
```

ATM fee is in `%base_currency` (destination/wallet currency — ATM charges in local currency). Bank fee is in `%withdrawal_source_currency` (bank charges in its own currency).

### 3. `ProcessedTransaction.py` — `to_hledger_dict()`

Change `withdrawal_bank_fx_fee` to always populate with "0.0" default instead of empty string:

Current (line 74-77):
```python
if wm.bank_fx_fee is not None:
    data["withdrawal_bank_fx_fee"] = str(wm.bank_fx_fee)
else:
    data["withdrawal_bank_fx_fee"] = ""
```

Change to:
```python
data["withdrawal_bank_fx_fee"] = str(wm.bank_fx_fee) if wm.bank_fx_fee is not None else "0.0"
```

### 4. `account_parser.py` — `parse_withdrawal_answers()`

Bank fee is now always present in TUI answers. The current code already parses it when found by caption matching (`elif caption == "Bank fee (in source currency, 0 if none):"`) so no change needed. But `bank_fee` is initialized as `None` — change to `0.0` to match `atm_fee`:

Current (line 321): `bank_fee = None`
Change to: `bank_fee = 0.0`

This ensures `WithdrawalMetadata.bank_fx_fee` is always a float (never None) for both domestic and foreign.

### 5. `Receipt.py` — `WithdrawalMetadata`

Consider changing `bank_fx_fee: Optional[float] = None` to `bank_fx_fee: float = 0.0` since it's now always asked. This is optional but makes the type cleaner. If changed, also update `_convert_withdrawal_metadata()` to handle old JSON files that may have `null` for this field.

### 6. Tests — `test_withdrawal_tui_and_journal.py`

- `test_domestic_withdrawal_dict_has_source_account`: expect `withdrawal_bank_fx_fee` = `"0.0"` (was `""`)
- Update/add rules tests: domestic rule now has `expenses:atm:operator-fee` and `expenses:fees:bank` postings
- Foreign rule now has `expenses:fees:bank` posting
- Add test for bank fee question always being created (like existing `test_creates_atm_fee_question`)

### 7. `_prefill_withdrawal_from_metadata()` in `reconfiguration.py`

Already prefills bank fee (line 791-793). No change needed — it uses `metadata.bank_fx_fee if metadata.bank_fx_fee is not None else 0.0`.

## Validation logic pseudocode

In `handle_post_account_withdrawal_questions()`, after rebuilding the TUI and setting answers:

```python
BANK_FEE_QUESTION = "Bank fee (in source currency, 0 if none):"

if not is_foreign:
    amount_debited = _get_tui_answer(new_tui, AMOUNT_DEBITED_QUESTION)
    change_returned = _get_tui_answer(new_tui, "Change returned to account:")
    atm_fee = _get_tui_answer(new_tui, ATM_FEE_QUESTION)
    bank_fee = _get_tui_answer(new_tui, BANK_FEE_QUESTION)

    if all(v is not None for v in [amount_debited, change_returned, atm_fee, bank_fee]):
        debited = round(float(amount_debited), 2)
        expected = round(float(change_returned) + float(atm_fee) + float(bank_fee), 2)
        # Find the bank fee widget to highlight
        for inp in new_tui.inputs:
            w = inp.base_widget
            if hasattr(w, "question_data") and w.question_data.question == BANK_FEE_QUESTION:
                if debited != expected:
                    inp.set_attr_map({None: "error"})
                else:
                    inp.set_attr_map({None: "normal"})
                break
```

## Summary of question order after changes

```
Toggle (y/n)
  → Withdrawal source account
  → Source account currency
  → Amount debited from source account
  → [Wallet account, Currency, Change returned, Add another]
  → ATM operator fee (always, default 0)
  → Bank fee (always, default 0)
  → Exchange rate (foreign only)
```
