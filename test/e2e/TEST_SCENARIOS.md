# E2E Test Scenarios for start.sh

This document tracks the desired test scenarios for `./start.sh` and related functionality, based on GitHub issues.

## Status Legend

- [ ] Not implemented
- [x] Implemented
- [~] Partially implemented

---

## Core Pipeline Tests (Issue #142)

**Goal:** Demonstrate and test the full `./start.sh` pipeline from CSV input to plot visualization.

| # | Scenario | Test File | Gif | Status |
|---|----------|-----------|-----|--------|
| 1.1 | Full pipeline runs without errors | `test_start_sh.py` | `start_sh_full_pipeline/` | [ ] |
| 1.2 | `all-years.journal` created and valid | `test_start_sh.py` | - | [ ] |
| 1.3 | `asset_transaction_csvs/` populated | `test_start_sh.py` | - | [ ] |
| 1.4 | SVG plots generated in `hledger_plots/` | `test_start_sh.py` | - | [ ] |
| 1.5 | Dash app starts on localhost:8050 | `test_dash_app.py` | - | [ ] |
| 1.6 | Dash app period dropdown works | `test_dash_app.py` | - | [ ] |

---

## Preprocess Assets Phase (Issue #143)

**Goal:** Test `hledger_preprocessor --preprocess-assets` in isolation.

| # | Scenario | Test File | Gif | Status |
|---|----------|-----------|-----|--------|
| 2.1 | Preprocess assets creates CSV directory | `test_preprocess_assets.py` | `preprocess_assets/` | [ ] |
| 2.2 | Asset CSVs contain correct transaction format | `test_preprocess_assets.py` | - | [ ] |
| 2.3 | `.rules` files generated for asset accounts | `test_preprocess_assets.py` | - | [ ] |

---

## hledger-flow Import Phase (Issue #144)

**Goal:** Test `hledger-flow import` converting CSVs to journals.

| # | Scenario | Test File | Gif | Status |
|---|----------|-----------|-----|--------|
| 3.1 | hledger-flow import creates journal structure | `test_hledger_flow_import.py` | `hledger_flow_import/` | [ ] |
| 3.2 | Import directory structure correct | `test_hledger_flow_import.py` | - | [ ] |
| 3.3 | Journal files pass `hledger check` | `test_hledger_flow_import.py` | - | [ ] |

---

## Account Setup (Issue #145)

**Goal:** Test `hledger_preprocessor --new-setup` for account configuration.

| # | Scenario | Test File | Gif | Status |
|---|----------|-----------|-----|--------|
| 4.1 | New setup wizard completes | `test_new_setup.py` | `new_setup/` | [ ] |
| 4.2 | Config file generated correctly | `test_new_setup.py` | - | [ ] |

---

## Receipt Entry (Issue #140)

**Goal:** Test TUI for entering a receipt manually.

| # | Scenario | Test File | Gif | Status |
|---|----------|-----------|-----|--------|
| 5.1 | TUI launches and displays receipt image | `test_receipt_entry.py` | `receipt_entry/` | [ ] |
| 5.2 | User can enter date, shop, category | `test_receipt_entry.py` | - | [ ] |
| 5.3 | Receipt saved to JSON correctly | `test_receipt_entry.py` | - | [ ] |

---

## Receipt-to-CSV Linking (Issue #141)

**Goal:** Test linking receipts to CSV transactions.

| # | Scenario | Test File | Gif | Status |
|---|----------|-----------|-----|--------|
| 6.1 | 1 CSV txn ↔ 1 receipt (pin payment) | `test_receipt_linking.py` | `receipt_linking/` | [ ] |
| 6.2 | 1 CSV txn ↔ 2 receipt AccountTxns (pin + partial cash) | `test_receipt_linking.py` | - | [ ] |

---

## Payment Scenarios (Issue #139)

**Goal:** Test various payment type combinations through the pipeline.

| # | Scenario | Description | Status |
|---|----------|-------------|--------|
| 7.A | Pin only | AccountTransaction linked to GenericCSVTransaction | [ ] |
| 7.B.0.0 | Pin + cash (withdrawal) | Cash = -pin, cash outputted to CSV | [ ] |
| 7.B.0.1 | Pin + cash (complementary) | pin + cash payment, cash to CSV | [ ] |
| 7.B.0.2 | Pin + cash (partial) | Partial payment/withdrawal | [ ] |
| 7.C.0 | Cash only (same currency) | All outputted to CSV | [ ] |
| 7.C.1 | Cash only (different currencies) | Currency handling test | [ ] |
| 7.D | Pin + cash (different currencies) | Complex multi-currency | [ ] |

---

## Error Handling (Issue #41)

**Goal:** Test user-friendly error display for common issues.

| # | Scenario | Test File | Status |
|---|----------|-----------|--------|
| 8.1 | Uncategorized transaction shows helpful error | `test_error_handling.py` | [ ] |
| 8.2 | Missing CSV file error is clear | `test_error_handling.py` | [ ] |

---

## Existing Tests

| Test File | Description | Covers |
|-----------|-------------|--------|
| `test_gif_generation.py` | Existing gif generation test | TUI receipt editing |

---

## Related Issues Summary

| Issue | Title | Milestone |
|-------|-------|-----------|
| #142 | Create test setup that shows how to run .start.sh up to and including plot | gifs |
| #143 | Create test and cli that shows how to run --preprocess-assets | gifs |
| #144 | Create test and cli gif that shows how to run hledger-flow | gifs |
| #145 | Create test and gif for hledger_preprocessor --new-setup for accounts | gifs |
| #140 | Create test setup and gif that shows how one can enter a receipt | gifs |
| #141 | Create test setup and gif that shows how to link 2 receipts to 2 CSV transactions | gifs |
| #139 | Matching (payment scenarios) | - |
| #41 | Make sure the user gets: "transaction uncategorised error" directly | Useful for other people |
