# Withdrawals

## Overview

ATM withdrawals involve two accounts: a source bank account (e.g. Triodos) and a destination wallet (e.g. wallet:physical). The system handles this via:

1. **TUI receipt labelling** — captures withdrawal metadata (source account, fees, exchange rate)
2. **Withdrawal metadata injection** — metadata flows into the preprocessed CSV
3. **4-posting hledger rules** — produce correct journal entries with fee postings

## Withdrawal Metadata

`WithdrawalMetadata` dataclass (in `TransactionObjects/Receipt.py`):
- `source_account_transaction` — the bank-side transaction
- `atm_operator_fee` — ATM fee (always populated, default 0.0)
- `bank_fx_fee` — bank fee (Optional[float], None for older receipts)
- `exchange_rate` — for foreign currency (Optional[float])
- `withdrawn_amount` — non-empty only for foreign currency

## TUI Question Flow (when withdrawal toggle = "y")

1. Withdrawal source account (VerticalMultipleChoice)
2. Source account currency (VerticalMultipleChoice)
3. Amount debited from source account (FLOAT)
4. Wallet account, Currency, Change returned, Add another
5. ATM operator fee (FLOAT, default 0) — **always asked**
6. Bank fee (FLOAT, default 0) — **always asked** (was foreign-only, now always)
7. Exchange rate (FLOAT, default 1) — **foreign only**

### Domestic Balance Check
`amount_debited == change_returned + atm_fee + bank_fee`

## Journal Examples

### Domestic (EUR → EUR)
```
2025-03-30 ATM Withdrawal
    assets:at:wallet:physical        320.00 EUR  ; cash received
    expenses:atm:operator-fee          5.00 EUR  ; ATM fee
    expenses:fees:bank                 5.00 EUR  ; bank fee
    assets:at:triodos:checking      -330.00 EUR  ; total debited
```

### Foreign (EUR → GBP)
```
2025-03-30 ATM Withdrawal (foreign currency)
    assets:at:wallet:physical        100.00 GBP
    expenses:atm:operator-fee          3.00 GBP  ; ATM fee (dest currency)
    expenses:fees:bank                 2.00 EUR  ; bank fee (source currency)
    assets:at:triodos:checking      -130.00 EUR  ; total debited
```

## Wallet-Side Suppression

When a withdrawal receipt has `withdrawal_metadata` and the source account has its own CSV, the wallet-side journal entry is **skipped** to avoid double-counting. This is handled by `_should_skip_withdrawal_transaction()` in `main_manager.py`.

The bank CSV (e.g. Triodos) produces the authoritative journal entry. The wallet CSV only contains spending transactions (groceries from withdrawn cash), not the withdrawal itself.

## CSV Columns (populated by `to_hledger_dict()`)

| Column | Source |
|--------|--------|
| `withdrawal_source_account` | `wm.source_account_transaction.account` |
| `withdrawal_source_amount` | `wm.source_account_transaction.tendered_amount_out` |
| `withdrawal_source_currency` | `wm.source_account_transaction.account.base_currency` |
| `withdrawal_atm_fee` | `wm.atm_operator_fee` |
| `withdrawal_dest_amount` | `wm.withdrawn_amount` (non-empty only for foreign) |
| `withdrawal_exchange_rate` | `wm.exchange_rate` |
| `withdrawal_bank_fx_fee` | `wm.bank_fx_fee` |

## Key Files

| File | Purpose |
|------|---------|
| `tui-image-labeller/.../WithdrawalQuestions.py` | Withdrawal question data objects |
| `tui-image-labeller/.../reconfiguration.py` | Post-account question injection, toggle, prefill |
| `tui-image-labeller/.../account_parser.py` | `parse_withdrawal_answers()` → `WithdrawalMetadata` |
| `TransactionObjects/Receipt.py` | `WithdrawalMetadata` dataclass |
| `TransactionObjects/ProcessedTransaction.py` | `to_hledger_dict()` — maps metadata → CSV columns |
| `rules/generate_rules_content.py` | `_create_withdrawal_rules()` — generates hledger rules |
| `management/main_manager.py` | `_should_skip_withdrawal_transaction()` |
| `test/test_withdrawal_tui_and_journal.py` | All withdrawal tests |

## Receipt–CSV Transaction Matching

When a receipt targets an account with a bank CSV, the receipt's transaction should be linked to the matching CSV row. This enables:
1. Withdrawal metadata injection into the bank CSV's preprocessed row
2. Bank-side journal entry using the 4-posting withdrawal rules
3. Early mismatch detection

Currently, wallet-side withdrawal entries are skipped when the source bank has a CSV. The bank CSV preprocessing classifies each row but receipt-to-CSV linking for metadata injection is a separate (future) integration step.
