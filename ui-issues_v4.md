# UI Issues v4 — Corrected DAG Sequences per User Story

This document completes `ui-issues_v3.md` by defining, for every user story
that has a DAG path, the exact sequence of nodes to show in each view mode.

The intent (from v3): the **Segment** view shows only the nodes that are DIRECTLY RELEVANT TO THE USERSTORY. The **Full path** view shows the
complete start-to-end data flow for that usersstory. It shows nodes that may influence the nodes directly relevant for the userstory, and it shows the nodes later in the normal hledger-preprocessor flow that may be influenced by the information/activites/choices made in the nodes directly relevant to the userstor. Furthermore, it shows ONLY visited nodes, no
unvisited/unused paralel nodes of that layer (that are not relevant for the userstory at all).

## Both views show **only** the nodes that belong to that story's YAML `paths`. No node that is not in the story's `paths` should appear.

## Resolved v3 issues

| v3 issue                                    | Status                                                               |
| ------------------------------------------- | -------------------------------------------------------------------- |
| Remove acceptance criteria from story pages | **Done** — still in YAML for documentation but can be hidden in HTML |
| Toggle between segment and full-path DAG    | **Done** — Segment/Full toggle implemented in `dag-sync.js`          |
| Left-align DAG levels                       | **Done** — direct SVG generator in `generate_overview_svg_direct()`  |
| Box around configuration sublevels          | **Done** — config group box in overview SVG                          |
| Lower opacity of non-used nodes             | **Done** — `--dim-opacity` parameter                                 |

## Remaining v3 issues (to implement)

### 0. The navigation nodes at the bottom should go away,

The DAG on the side should be used for navigation (and highlighting of current position of gif in user story example flow). (in the view of the userstories).

### 1. Segment view shows too many nodes

Currently the segment view shows the per-story isolated PlantUML SVG, which
renders all nodes in the story's `paths` — including config nodes that the
GIF does not step through. The segment view should show only the `demo_paths`
nodes (or, for stories without `demo_paths`, fall back to `paths`).

### 2. Full-path view shows wrong nodes

The full-path view currently shows the complete overview SVG (all stories'
nodes) with unreachable nodes dimmed. Instead it should show only the nodes
from that story's `paths` — no other nodes at all. Additionally it should
highlight (e.g. section-box) the layers that are the focus of the story's
section.

### 3. Matching outcome flow

The matching outcome section should show the recursive retry loop: widen date
-> retry, widen amount -> retry, swap DD/MM -> retry, correct receipt -> retry.
All paths lead back to "try to match" until a match is found.

### 4. Journal output display

The journal output section should show the `.journal` folder structure based
on `config.yaml` account configs, then display the relevant `.journal` file
content with the story's postings.

______________________________________________________________________

## Per-story DAG sequences

For each story with DAG paths, two sequences are defined:

- **Segment**: only the nodes directly relevant to the user story — the
  layers/nodes that are the story's core concern.
- **Full path** (`paths`): the complete start-to-end data flow for the story.
  Includes upstream nodes that influence the story and downstream nodes
  influenced by it. Only visited nodes — no parallel unused nodes from the
  same layer.

Multi-path stories (branches) show each branch on a separate line.
Stories without `paths` (marked `no_dag_reason` in YAML) are omitted.

______________________________________________________________________

### Step 1a: Account Configuration

#### US-1a.1 — Single bank + CSV

Story: configure one bank account with CSV import.

- **Segment**: acct_triodos_csv
- **Full path**: acct_triodos_csv, dirp_default, fnames_default, catcfg_default, malgo_default

#### US-1a.2 — Multiple banks

Story: configure multiple bank accounts.

- **Segment**: acct_triodos_csv, acct_ing_csv
- **Full path**: acct_triodos_csv, acct_ing_csv, dirp_default, fnames_default, catcfg_default, malgo_default

#### US-1a.3 — Cash wallet (no CSV)

Story: configure a cash wallet (no CSV).

- **Segment**: acct_eur_wallet
- **Full path**: acct_eur_wallet, dirp_default, fnames_default, catcfg_default

#### US-1a.4 — Crypto exchange

Story: configure a crypto exchange account alongside a bank account.

- **Segment**: acct_btc_wallet
- **Full path**: acct_triodos_csv, acct_btc_wallet, dirp_default, fnames_default, catcfg_default, malgo_default

#### US-1a.5 — Matching algorithm parameters

Story: configure the matching algorithm's tolerances.

- **Segment**: malgo_default
- **Full path**: acct_triodos_csv, acct_ing_csv, acct_eur_wallet, dirp_default, fnames_default, catcfg_default, malgo_default

#### US-1a.6 — Base currency

Story: set base_currency for each account.

- **Segment**: acct_triodos_csv, acct_eur_wallet, acct_gbp_wallet, acct_btc_wallet, acct_gold_wallet, acct_silver_wallet
- **Full path**: acct_triodos_csv, acct_eur_wallet, acct_gbp_wallet, acct_btc_wallet, acct_gold_wallet, acct_silver_wallet, dirp_default, fnames_default, catcfg_default, malgo_default

______________________________________________________________________

### Step 1b: Category Configuration

#### US-1b.1 — Hierarchical categories

Story: define spending categories in categories.yaml.

- **Segment**: cat_basic
- **Full path**: acct_triodos_csv, acct_eur_wallet, dirp_default, fnames_default, catcfg_default, malgo_default, cat_basic, match_default, start_2024_1000eur, csv_ekoplaza_4217_jan15, img_ekoplaza_card, lbl_ekoplaza_card_eur, out_auto_1hit, jrnl_groceries_ekoplaza

#### US-1b.3 — Income categories

Story: define income categories alongside expense categories.

- **Segment**: cat_with_income
- **Full path**: acct_triodos_csv, acct_eur_wallet, dirp_default, fnames_default, catcfg_default, malgo_default, cat_with_income, match_default, start_2024_1000eur, csv_salary_3000, lbl_salary_credit, out_csv_only_classify, jrnl_income_salary

______________________________________________________________________

### Step 2b: Receipt Labelling

#### US-2b.1 — Label card receipt (EUR)

Story: label a receipt paid by card, selecting account and category in TUI.

- **Segment**: img_ekoplaza_card, lbl_ekoplaza_card_eur
- **Full path**: acct_triodos_csv, acct_eur_wallet, dirp_default, fnames_default, catcfg_default, malgo_default, cat_basic, match_default, start_2024_1000eur, csv_ekoplaza_4217_jan15, img_ekoplaza_card, lbl_ekoplaza_card_eur, out_auto_1hit, jrnl_groceries_ekoplaza

#### US-2b.2 — Label cash receipt

Story: label a receipt paid by cash, selecting the wallet account.

- **Segment**: img_coffee_cash, lbl_coffee_cash
- **Full path**: acct_triodos_csv, acct_eur_wallet, dirp_default, fnames_default, catcfg_default, malgo_default, cat_basic, match_default, start_2024_1000eur, img_coffee_cash, lbl_coffee_cash, out_skip_cash, jrnl_coffee_cash

#### US-2b.3 — Label foreign-currency receipt

Story: label a receipt in GBP while account is EUR.

- **Segment**: img_atm_gbp, lbl_atm_100gbp
- **Full path**: acct_triodos_csv, acct_eur_wallet, acct_gbp_wallet, acct_btc_wallet, acct_gold_wallet, acct_silver_wallet, dirp_default, fnames_default, catcfg_default, malgo_default, cat_basic, match_default, start_2024_1000eur, csv_atm_gbp_11750, img_atm_gbp, lbl_atm_100gbp, out_currency_convert, jrnl_wallet_gbp, jrnl_triodos_debit_gbp

#### US-2b.4 — Label split-payment receipt

Story: label a receipt split across card + cash.

- **Segment**: img_split_dinner, lbl_dinner_split
- **Full path** (2 branches):
  1. acct_triodos_csv, acct_eur_wallet, dirp_default, fnames_default, catcfg_default, malgo_default, cat_extended, match_default, start_2024_1000eur, csv_split_dinner_30, img_split_dinner, lbl_dinner_split, out_auto_1hit, jrnl_dinner_split_card
  1. acct_triodos_csv, acct_eur_wallet, dirp_default, fnames_default, catcfg_default, malgo_default, cat_extended, match_default, start_2024_1000eur, img_split_dinner, lbl_dinner_split, out_skip_cash, jrnl_dinner_split_cash

#### US-2b.5 — Label receipt with returns

Story: label a receipt with bought + returned items.

- **Segment**: img_return_item, lbl_return_item
- **Full path**: acct_triodos_csv, acct_eur_wallet, dirp_default, fnames_default, catcfg_default, malgo_default, cat_basic, match_default, start_2024_1000eur, img_return_item, lbl_return_item, out_auto_1hit, jrnl_return_net

______________________________________________________________________

### Step 3: Receipt-to-CSV Transaction Matching

#### US-3.1 — Auto-match same currency

Story: auto-link receipt to CSV when exactly 1 match on date+amount.

- **Segment**: csv_ekoplaza_4217_jan15, lbl_ekoplaza_card_eur, out_auto_1hit
- **Full path**: acct_triodos_csv, dirp_default, fnames_default, catcfg_default, malgo_default, cat_basic, match_default, start_2024_1000eur, csv_ekoplaza_4217_jan15, img_ekoplaza_card, lbl_ekoplaza_card_eur, out_auto_1hit, jrnl_groceries_ekoplaza

#### US-3.2 — Foreign currency match

Story: match a GBP receipt to an EUR bank CSV using conversion rate.

- **Segment**: csv_atm_gbp_11750, lbl_atm_100gbp, out_currency_convert
- **Full path** (2 branches):
  1. acct_triodos_csv, acct_eur_wallet, acct_gbp_wallet, acct_btc_wallet, acct_gold_wallet, acct_silver_wallet, dirp_default, fnames_default, catcfg_default, malgo_default, cat_basic, match_default, start_2024_1000eur, csv_atm_gbp_11750, img_atm_gbp, lbl_atm_100gbp, out_currency_convert, jrnl_wallet_gbp
  1. acct_triodos_csv, acct_eur_wallet, acct_gbp_wallet, acct_btc_wallet, acct_gold_wallet, acct_silver_wallet, dirp_default, fnames_default, catcfg_default, malgo_default, cat_basic, match_default, start_2024_1000eur, csv_atm_gbp_11750, img_atm_gbp, lbl_atm_100gbp, out_currency_convert, jrnl_triodos_debit_gbp

#### US-3.3 — Widen date range

Story: widen date tolerance when no match found (bank posted 3 days late).

- **Segment**: match_narrow, csv_delayed_jan18, lbl_delayed_shop, out_widen_date
- **Full path**: acct_triodos_csv, acct_eur_wallet, dirp_default, fnames_default, catcfg_default, malgo_default, cat_basic, match_narrow, start_2024_1000eur, csv_delayed_jan18, img_delayed_shop, lbl_delayed_shop, out_widen_date, jrnl_delayed_shop

#### US-3.4 — Widen amount range

Story: widen amount tolerance when bank rounded the amount.

- **Segment**: csv_rounded_5000, lbl_rounded_shop, out_widen_amount
- **Full path**: acct_triodos_csv, acct_eur_wallet, dirp_default, fnames_default, catcfg_default, malgo_default, cat_basic, match_default, start_2024_1000eur, csv_rounded_5000, img_rounded_shop, lbl_rounded_shop, out_widen_amount, jrnl_rounded_shop

#### US-3.5 — Swap DD/MM

Story: auto-swap day/month when date formats are ambiguous.

- **Segment**: csv_swapped_date, lbl_swapped_date, out_swap_dd_mm
- **Full path**: acct_triodos_csv, acct_eur_wallet, dirp_default, fnames_default, catcfg_default, malgo_default, cat_basic, match_default, start_2024_1000eur, csv_swapped_date, img_swapped_date, lbl_swapped_date, out_swap_dd_mm, jrnl_swapped_shop

#### US-3.6 — Disambiguate 2–14 matches

Story: select the correct transaction from a ranked candidate list.

- **Segment**: csv_ekoplaza_4217_jan15, csv_ekoplaza_4217_jan14, csv_ekoplaza_4300_jan16, lbl_ekoplaza_card_eur, out_disambiguate_3
- **Full path** (3 branches):
  1. acct_triodos_csv, acct_eur_wallet, dirp_default, fnames_default, catcfg_default, malgo_default, cat_basic, match_wide_date, start_2024_1000eur, csv_ekoplaza_4217_jan15, img_ekoplaza_card, lbl_ekoplaza_card_eur, out_disambiguate_3, jrnl_groceries_ekoplaza
  1. acct_triodos_csv, acct_eur_wallet, dirp_default, fnames_default, catcfg_default, malgo_default, cat_basic, match_wide_date, start_2024_1000eur, csv_ekoplaza_4217_jan14, img_ekoplaza_card, lbl_ekoplaza_card_eur, out_disambiguate_3, jrnl_groceries_ekoplaza
  1. acct_triodos_csv, acct_eur_wallet, dirp_default, fnames_default, catcfg_default, malgo_default, cat_basic, match_wide_date, start_2024_1000eur, csv_ekoplaza_4300_jan16, img_ekoplaza_card, lbl_ekoplaza_card_eur, out_disambiguate_3, jrnl_groceries_ekoplaza

#### US-3.7 — Too many matches (15+)

Story: reduce scope when 15+ candidates found.

- **Segment**: match_wide_both, csv_ekoplaza_4217_jan15, lbl_ekoplaza_card_eur, out_too_many_reduce
- **Full path**: acct_triodos_csv, acct_eur_wallet, dirp_default, fnames_default, catcfg_default, malgo_default, cat_basic, match_wide_both, start_2024_1000eur, csv_ekoplaza_4217_jan15, img_ekoplaza_card, lbl_ekoplaza_card_eur, out_too_many_reduce

#### US-3.8 — Correct receipt inline

Story: fix a receipt label during matching without leaving the flow.

- **Segment**: lbl_ekoplaza_card_eur, out_correct_receipt, out_auto_1hit
- **Full path**: acct_triodos_csv, acct_eur_wallet, dirp_default, fnames_default, catcfg_default, malgo_default, cat_basic, match_default, start_2024_1000eur, csv_ekoplaza_4217_jan15, img_ekoplaza_card, lbl_ekoplaza_card_eur, out_correct_receipt, out_auto_1hit, jrnl_groceries_ekoplaza

#### US-3.9 — Direct asset purchase (gold)

Story: match a gold purchase receipt (GRAMS) to EUR bank CSV.

- **Segment**: csv_gold_dealer_580, lbl_gold_10g, out_asset_convert
- **Full path** (2 branches):
  1. acct_triodos_csv, acct_eur_wallet, acct_gbp_wallet, acct_btc_wallet, acct_gold_wallet, acct_silver_wallet, dirp_default, fnames_default, catcfg_default, malgo_default, cat_extended, match_default, start_2024_1000eur, csv_gold_dealer_580, img_gold, lbl_gold_10g, out_asset_convert, jrnl_asset_gold
  1. acct_triodos_csv, acct_eur_wallet, acct_gbp_wallet, acct_btc_wallet, acct_gold_wallet, acct_silver_wallet, dirp_default, fnames_default, catcfg_default, malgo_default, cat_extended, match_default, start_2024_1000eur, csv_gold_dealer_580, img_gold, lbl_gold_10g, out_asset_convert, jrnl_triodos_debit_gold

#### US-3.10 — Skip cash-only receipt

Story: matcher auto-skips receipts on wallet accounts (no CSV).

- **Segment**: lbl_bike_cash, out_skip_cash
- **Full path**: acct_triodos_csv, acct_eur_wallet, dirp_default, fnames_default, catcfg_default, malgo_default, cat_basic, match_default, start_2024_1000eur, img_bike_repair, lbl_bike_cash, out_skip_cash, jrnl_repairs_bike

#### US-3.11 — Withdrawal + fees (NOT YET IMPLEMENTED)

Story: match a foreign withdrawal with bank fee split.

- **Segment**: csv_atm_gbp_23750_fee, lbl_atm_200gbp_fee, out_currency_convert_fee
- **Full path** (2 branches):
  1. acct_triodos_csv, acct_eur_wallet, acct_gbp_wallet, acct_btc_wallet, acct_gold_wallet, acct_silver_wallet, dirp_default, fnames_default, catcfg_default, malgo_default, cat_extended, match_default, start_2024_1000eur, csv_atm_gbp_23750_fee, img_atm_gbp_fee, lbl_atm_200gbp_fee, out_currency_convert_fee, jrnl_wallet_gbp_200
  1. acct_triodos_csv, acct_eur_wallet, acct_gbp_wallet, acct_btc_wallet, acct_gold_wallet, acct_silver_wallet, dirp_default, fnames_default, catcfg_default, malgo_default, cat_extended, match_default, start_2024_1000eur, csv_atm_gbp_23750_fee, img_atm_gbp_fee, lbl_atm_200gbp_fee, out_currency_convert_fee, jrnl_bankfees

#### US-3.14 — Duplicate blocked

Story: prevent linking same CSV transaction to two receipts.

- **Segment**: csv_ekoplaza_4217_jan15, lbl_ekoplaza_card_eur, out_duplicate_blocked
- **Full path**: acct_triodos_csv, acct_eur_wallet, dirp_default, fnames_default, catcfg_default, malgo_default, cat_basic, match_default, start_2024_1000eur, csv_ekoplaza_4217_jan15, img_ekoplaza_card, lbl_ekoplaza_card_eur, out_duplicate_blocked

______________________________________________________________________

### Step 4: Pipeline Execution

#### US-4.1 — Full pipeline

Story: run the entire pipeline end-to-end with one command.

- **Segment**: all nodes (the full pipeline IS the direct concern)
- **Full path** (2 branches):
  1. acct_triodos_csv, acct_eur_wallet, dirp_default, fnames_default, catcfg_default, malgo_default, cat_basic, match_default, start_2024_1000eur, csv_ekoplaza_4217_jan15, img_ekoplaza_card, lbl_ekoplaza_card_eur, out_auto_1hit, jrnl_groceries_ekoplaza, viz_sankey
  1. acct_triodos_csv, acct_eur_wallet, dirp_default, fnames_default, catcfg_default, malgo_default, cat_basic, match_default, start_2024_1000eur, csv_ekoplaza_4217_jan15, img_ekoplaza_card, lbl_ekoplaza_card_eur, out_auto_1hit, jrnl_groceries_ekoplaza, viz_treemap

______________________________________________________________________

### Step 5: Visualisation

#### US-5.1 — Sankey diagram

Story: generate a Sankey diagram from journal data.

- **Segment**: jrnl_groceries_ekoplaza, viz_sankey
- **Full path**: acct_triodos_csv, acct_eur_wallet, dirp_default, fnames_default, catcfg_default, malgo_default, cat_basic, match_default, start_2024_1000eur, jrnl_groceries_ekoplaza, viz_sankey

#### US-5.2 — Treemap plot

Story: generate a Treemap from journal data.

- **Segment**: jrnl_groceries_ekoplaza, viz_treemap
- **Full path**: acct_triodos_csv, acct_eur_wallet, dirp_default, fnames_default, catcfg_default, malgo_default, cat_basic, match_default, start_2024_1000eur, jrnl_groceries_ekoplaza, viz_treemap

______________________________________________________________________

### Classification

#### US-C.1 — Classify transactions using rule-based logic

Story: classify a CSV transaction without a receipt using rules/AI.

- **Segment**: csv_ekoplaza_4217_jan15, out_csv_only_classify
- **Full path**: acct_triodos_csv, acct_eur_wallet, dirp_default, fnames_default, catcfg_default, malgo_default, cat_basic, match_default, start_2024_1000eur, csv_ekoplaza_4217_jan15, out_csv_only_classify, jrnl_groceries_ekoplaza

______________________________________________________________________

### Cross-cutting

#### US-X.6 — Enforce one receipt image per transaction

Story: enforce 1:1 relationship between receipt image and label.

- **Segment**: img_ekoplaza_card, lbl_ekoplaza_card_eur
- **Full path**: img_ekoplaza_card, lbl_ekoplaza_card_eur
