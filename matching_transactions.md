# User Stories: Receipt–CSV Transaction Matching

## Context

When a receipt involves an account that has a bank CSV (e.g. triodos:checking),
the receipt's transaction must be **linked** to the corresponding row in that
bank CSV. This linking is necessary so that:

1. Withdrawal metadata (fees, source account, exchange rate) is injected into the
   bank CSV's preprocessed row, enabling hledger's multi-posting withdrawal rules.
2. The bank-side journal entry uses `equity:clearing` (not the destination asset
   account) to avoid double-counting — the wallet-side entry is authoritative.
3. The system can detect mismatches between receipt labels and bank data early,
   rather than silently producing wrong journal entries.

### Current state

- **Wallet-side withdrawal entries are skipped** when the source bank has a CSV
  (`_should_skip_withdrawal_transaction()` in `main_manager.py:61–75`).
- **Bank CSV preprocessing** (`preprocess_generic_csvs`) classifies each CSV row
  but never links it to a receipt — `parent_receipt` is always `None`.
- The triodos CSV therefore produces a simple 2-posting transfer for withdrawals
  (e.g. `assets:at:wallet:physical / assets:at:triodos:checking`) with no fee
  postings and no `equity:clearing`.
- **Receipt-to-CSV matching** exists (`matching/` module) but runs in a separate
  phase that is not called from `start.sh`, and does not feed back into CSV
  preprocessing.
- **Bitvavo↔triodos transfers** already use `equity:clearing` via the
  `linked_accounts` config + generated rules. This must remain working.

### Corrected withdrawal arithmetic

A withdrawal of 320 EUR with ATM fee 50 EUR and bank fee 20 EUR means:

```
wallet received:              250 EUR  (320 − 50 − 20)
ATM operator fee:              50 EUR
bank fee:                      20 EUR
total debited from bank:      320 EUR
```

The 4-posting journal entry:
```
assets:at:wallet:physical        250.00 EUR
expenses:atm:operator-fee        50.00 EUR
expenses:fees:bank                20.00 EUR
assets:at:triodos:checking     -320.00 EUR
```

Balance check: `amount_debited (320) == change_returned (250) + atm_fee (50) + bank_fee (20)`.

---

## User Story 1: Auto-link receipt account to CSV transaction in the TUI

### As a user, when I specify an account with a CSV, a currency, and an amount in the TUI, the system should automatically find and link the matching CSV transaction.

**Acceptance criteria:**

1. When the user answers the "Belongs to bank/accounts_without_csv" question with
   an account that has a CSV, and then fills in "Currency" and
   "Amount paid from account" (or "Amount debited from source account" for
   withdrawals), the TUI should immediately search for matching CSV transactions.
2. The search uses the existing matching algorithm: date range
   (`config.matching_algo.days`) and amount tolerance
   (`config.matching_algo.amount_range`).
3. **If exactly 1 match is found**: auto-link it (set `original_transaction` on
   the receipt's `AccountTransaction`). Show a brief confirmation in the TUI
   (e.g. update the status bar or question colour to green).
4. **If multiple matches are found (2–14)**: present the candidates in the TUI
   and let the user pick one (like `handle_few_matches()` does today, but inline
   in the urwid TUI rather than on the CLI).
5. **If 0 matches are found**: show an error. Offer the user guidance:
   - "CSV may not cover this date — check that the bank CSV is up to date."
   - Option to widen the date range or amount tolerance and retry.
   - Option to swap day/month (EU date format quirk).
   - Option to skip linking (for accounts without CSV, this is fine; for accounts
     with CSV, warn that the journal will be incomplete).
6. The auto-link triggers on the reconfiguration pass — same mechanism as the
   existing `_try_background_withdrawal_match()` but generalised to all CSV
   accounts, not only withdrawals.

**Key files to modify:**

| File | Change |
|------|--------|
| `reconfiguration.py` | Generalise `_try_background_withdrawal_match()` into a function that runs for every account-with-CSV, not just withdrawal source accounts. Trigger after the amount question is answered. |
| `QuestionnaireApp` / TUI widgets | Add visual feedback (green/red highlight, status message) for match result. |
| `matching/searching/helper.py` | May need to expose `get_receipt_transaction_matches_in_csv_accounts()` for use from the TUI layer. |
| `ask_urwid_receipt.py` | Pass `csv_transactions_per_account` and `config` through to the reconfiguration layer (already partially done for withdrawals). |

---

## User Story 2: Inject withdrawal metadata into bank CSV row via receipt link

### As a user, when a receipt with withdrawal metadata is linked to a bank CSV transaction, the preprocessed CSV should contain the withdrawal columns so that hledger rules produce the correct 4-posting journal entry.

**Acceptance criteria:**

1. During `preprocess_generic_csvs()`, for each bank CSV transaction that has been
   linked to a receipt (via `original_transaction`), look up the matching receipt.
2. If that receipt has `withdrawal_metadata`, pass it as `parent_receipt` when
   creating the `ProcessedTransaction`.
3. `to_hledger_dict()` already injects `withdrawal_source_account`,
   `withdrawal_atm_fee`, `withdrawal_bank_fx_fee`, etc. when `parent_receipt` is
   set — this existing code handles the injection.
4. The generated hledger rules (already in place) then produce a 4-posting
   withdrawal entry from the bank-side CSV.
5. **Remove `_should_skip_withdrawal_transaction()`** — the wallet side no longer
   needs to produce the withdrawal entry; the bank side produces it via the
   linked receipt metadata.
6. The wallet-side CSV should still record the receipt's non-withdrawal
   transactions (groceries bought with the withdrawn cash, etc.), just not the
   withdrawal itself.

**Key files to modify:**

| File | Change |
|------|--------|
| `categorisation/categoriser.py` | In `classify_transactions()`, for `GenericCsvTransaction` instances, look up the linked receipt (via `original_transaction` hash matching against `labelled_receipts`) and pass it as `parent_receipt`. |
| `main_manager.py` | Remove `_should_skip_withdrawal_transaction()`. The wallet-side should NOT produce the withdrawal journal entry — the bank CSV handles it now. Keep skipping the wallet-side `AccountTransaction` for the withdrawal itself (the one whose account matches the wallet). |
| `ProcessedTransaction.py` | No change needed — `to_hledger_dict()` already injects withdrawal metadata when `parent_receipt` is set. |
| `preprocess_csvs.py` | Pass `labelled_receipts` through so `classify_transactions` can find matching receipts. (Already passed but not used for receipt lookup.) |

**Note:** Bitvavo↔triodos transfers must continue to work. Those use
`linked_accounts` config and `equity:clearing` rules, which are orthogonal to the
withdrawal metadata injection — no conflict.

---

## User Story 3: Bank-side withdrawal produces equity:clearing, not a direct transfer

### As a user, when a bank CSV withdrawal is linked to a receipt, the bank-side journal entry should use equity:clearing for the destination, and the wallet-side entry is authoritative.

**Acceptance criteria:**

1. Currently, the triodos rules classify a 320 EUR Geldmaat withdrawal as:
   ```
   assets:at:wallet:physical      EUR320.00    ← direct transfer
   assets:at:triodos:checking    EUR-320.00
   ```
   This must change. When a withdrawal is linked to a receipt, the bank CSV row
   gets withdrawal metadata injected (User Story 2), so the withdrawal rules
   match and produce the 4-posting entry instead of the generic transfer rule.

2. The 4-posting withdrawal rule on the bank side should produce:
   ```
   assets:at:wallet:physical        250.00 EUR   (change_returned)
   expenses:atm:operator-fee         50.00 EUR   (atm_fee)
   expenses:fees:bank                20.00 EUR   (bank_fee)
   assets:at:triodos:checking      -320.00 EUR   (balancing)
   ```

3. The wallet-side CSV should NOT contain a duplicate withdrawal entry. The
   wallet CSV only contains spending transactions (groceries, etc.) from the
   withdrawn cash.

4. **Unlinked bank CSV withdrawals** (no receipt label exists yet) should continue
   to produce the current 2-posting transfer. The withdrawal rules only match
   when `%withdrawal_source_account` is non-empty, which only happens when
   receipt metadata has been injected.

5. `equity:clearing` is NOT used for withdrawals — the 4-posting entry directly
   debits the bank account. `equity:clearing` remains only for simple transfers
   between two accounts that both have CSVs (e.g. triodos→bitvavo deposit).

---

## User Story 4: Fix wallet-side withdrawal amount (change_returned, not amount_debited)

### As a user, the wallet CSV's `amount` column for a withdrawal should reflect the cash received (change_returned), not the total debited.

**Acceptance criteria:**

1. The wallet-side `AccountTransaction` for a withdrawal has
   `change_returned = 250` and `tendered_amount_out = 0`. The net amount is
   `change_returned - tendered_amount_out = 250`. This is the amount that enters
   the wallet.
2. Since the withdrawal journal entry now lives on the bank side (User Story 2),
   the wallet CSV should not produce a withdrawal entry at all. But if wallet-side
   spending transactions exist (e.g. bought groceries for 44.30 from the 250 cash),
   those should appear normally.
3. The TUI balance check must use the corrected arithmetic:
   `amount_debited = change_returned + atm_fee + bank_fee`.
   So for `amount_debited=320, atm_fee=50, bank_fee=20`:
   `change_returned = 320 - 50 - 20 = 250`.

**Key files to modify:**

| File | Change |
|------|--------|
| `reconfiguration.py` | In the domestic prefill block, set "Change returned to account" to `amount_debited - atm_fee - bank_fee` (currently sets it to `amount_debited`). |
| `account_parser.py` | Verify that `change_returned` from the TUI is used as the wallet's amount, not `amount_debited`. |

---

## User Story 5: Ordering — receipt labelling before CSV preprocessing

### As a user, `start.sh` should run receipt labelling and CSV matching before CSV preprocessing, so that linked receipt metadata is available when bank CSVs are processed.

**Acceptance criteria:**

1. The current `start.sh` calls `hledger_preprocessor --preprocess-assets` which
   runs `manage_preprocessing_assets()` and `manage_preprocessing_csvs()`. Receipt
   matching (`manage_matching_manual_receipt_objs_to_account_transactions()`) is
   not called from `start.sh`.
2. The new order must be:
   1. Load receipt labels from disk.
   2. Run receipt-to-CSV matching (link receipts to bank CSV transactions).
   3. Preprocess bank CSVs (with linked receipt metadata injected).
   4. Preprocess asset CSVs (wallet spending, etc.).
   5. Generate rules files.
   6. Run `hledger-flow import`.
3. The matching step (step 2) should only run for receipts that are not yet linked
   (i.e. `original_transaction is None` for account transactions that target an
   account with a CSV).
4. If a receipt cannot be matched (CSV too old, no matching transaction), warn but
   continue — the bank CSV row will produce a 2-posting fallback entry.

**Key files to modify:**

| File | Change |
|------|--------|
| `start.sh` | Add a `--match-receipts` step before `--preprocess-assets`. |
| `main_manager.py` | Expose `manage_matching_manual_receipt_objs_to_account_transactions()` as a CLI action. Ensure it stores updated receipt labels (with `original_transaction` set) before CSV preprocessing runs. |

---

## User Story 6: Validate 4-posting balance for all withdrawal journal entries

### As a user, the system should verify that every withdrawal journal entry balances correctly: `amount_debited = change_returned + atm_fee + bank_fee`.

**Acceptance criteria:**

1. **TUI-side** (already partially implemented): The domestic balance check in
   `handle_post_account_withdrawal_questions()` highlights the bank fee question
   red when the 4 values don't balance.
2. **Export-side**: When `ProcessedTransaction.to_hledger_dict()` injects
   withdrawal metadata, verify the balance:
   `source_amount == (amount + atm_fee + bank_fee)` for domestic withdrawals.
   Log a warning if they don't match.
3. **Test**: Add an e2e test that creates a withdrawal receipt, runs the full
   pipeline, and verifies `hledger check` passes on the resulting journal.

---

## Dependency graph

```
US5 (ordering)
 ├── US1 (auto-link in TUI)
 │    └── US2 (inject metadata into bank CSV)
 │         ├── US3 (bank-side produces 4-posting, wallet-side skips withdrawal)
 │         └── US4 (fix wallet amount = change_returned)
 └── US6 (balance validation)
```

## Non-goals

- Changing the bitvavo↔triodos transfer flow. That uses `linked_accounts` +
  `equity:clearing` and is unaffected by these changes.
- Matching receipts to CSV transactions for non-withdrawal accounts that don't
  have a CSV (e.g. wallet:physical for groceries). Those don't need matching.
- Changing the hledger rules format or the `hledger-flow import` mechanism.
