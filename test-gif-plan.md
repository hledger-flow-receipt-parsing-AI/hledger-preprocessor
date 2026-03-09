# Test & GIF Plan for hledger-preprocessor User Stories

## Guiding Principle: No Fake Data

> **Do NOT FAKE CLI DATA, do not change the src code to make the outputs nice.
> GIFs ALWAYS show the true output generated when using the /src code.**
> Only the plotly GIFs still use fake data — do not build upon those.

All new tests and GIFs use the same pattern as `real_link_receipts_demo.py` and
`receipt_editor.py`: create a temp environment → run the real CLI → record with
asciinema → post-process to themed GIFs.

______________________________________________________________________

## 1. Current State: What Exists

### Existing Tests

| Layer       | File                           | Covers                               |
| ----------- | ------------------------------ | ------------------------------------ |
| Unit        | `test_hledger_dict.py`         | CSV column mapping (to_hledger_dict) |
| Unit        | `test_classification.py`       | Rule-based classification            |
| Integration | `test_config_loading.py`       | Load config YAML → Config object     |
| Integration | `test_hledger_postings.py`     | hledger journal import from CSV      |
| Integration | `test_new_flow.py`             | CLI `--new` creates import dirs      |
| E2E         | `test_gif_1a_setup_config.py`  | GIF generation: setup config         |
| E2E         | `test_gif_1b_add_category.py`  | GIF generation: add category         |
| E2E         | `test_gif_2a_crop_receipt.py`  | GIF generation: crop receipt         |
| E2E         | `test_gif_2b_label_receipt.py` | GIF generation: label receipt        |
| E2E         | `test_gif_3_match_receipt.py`  | GIF generation: match receipt to CSV |
| E2E         | `test_gif_4_run_pipeline.py`   | GIF generation: pipeline             |
| E2E         | `test_gif_5_show_plots.py`     | GIF generation: plots                |
| E2E         | `test_start_sh.py`             | Pipeline start.sh execution          |
| E2E         | `test_fixtures.py`             | Fixture structure validation         |

### Existing GIF Infrastructure

**Real output (pattern to follow):**

- `receipt_editor.py` — drives real urwid `--edit-receipt` TUI via `TuiNavigator`/pexpect
- `real_link_receipts_demo.py` — runs real `--link-receipts-to-transactions` CLI
- `real_rotate_crop_demo.py` — calls real `rotate_images()` and `crop_images()`
- `start_sh_demo.py` — runs real hledger pipeline commands

**Simulated (DO NOT extend):**

- `simulated_crop_demo.py`, `simulated_label_demo.py`, `simulated_config_demo.py`,
  `simulated_categories_demo.py`, `simulated_match_demo.py`

**Plotly (fake data — DO NOT build upon):**

- `show_plots_demo.py` uses generated data for Sankey/Treemap

### GIF Recording Pattern (from existing code)

```
1. generate.sh calls init_demo() from scripts/common.sh
2. Python demo module creates temp test environment:
   - mkdir dirs, write config.yaml, categories.yaml
   - create bank CSV with test transactions
   - seed receipt images + labels via PIL + JSON fixtures
3. asciinema rec captures the Python module running real CLI:
   - hledger_preprocessor --config {path} --edit-receipt
   - hledger_preprocessor --config {path} --link-receipts-to-transactions
4. TuiNavigator (pexpect.spawn) drives urwid TUI via keystrokes:
   - wait_for(pattern), press_down(), type_text(), press_enter()
   - KeyOverlay shows pressed keys in bottom-right corner
5. postprocess_cast() cleans ANSI escape sequences
6. asciinema-agg converts .cast → themed GIFs (8 themes)
7. gifsicle -O3 optimizes, ffmpeg converts to MP4
```

______________________________________________________________________

## 2. Coverage Matrix: User Stories × Tests × GIFs

### Legend

- `T:u` = unit test, `T:i` = integration test, `T:e` = E2E test
- `G:real` = GIF with real output, `G:sim` = GIF simulated (legacy)
- `---` = no coverage, **bold** = needs to be created

| Story   | Title                           | Status   | DAG | GIF    | Tests         |
| ------- | ------------------------------- | -------- | --- | ------ | ------------- |
| US-1a.1 | Single bank + CSV config        | IMPL     | yes | G:real | T:i           |
| US-1a.2 | Multiple bank accounts          | IMPL     | yes | ---    | ---           |
| US-1a.3 | Cash wallet (no CSV)            | IMPL     | yes | ---    | ---           |
| US-1a.4 | Crypto exchange                 | IMPL     | yes | ---    | ---           |
| US-1a.5 | Matching algorithm params       | IMPL     | yes | ---    | ---           |
| US-1a.6 | Base currency per account       | IMPL     | yes | ---    | ---           |
| US-1b.1 | Hierarchical categories         | IMPL     | yes | G:real | ---           |
| US-1b.2 | Add category (schema evolve)    | IMPL     | —   | ---    | ---           |
| US-1b.3 | Income categories               | IMPL     | yes | ---    | ---           |
| US-2a.1 | Rotate receipt image            | IMPL     | —   | G:real | ---           |
| US-2a.2 | Crop receipt image              | IMPL     | —   | G:real | ---           |
| US-2a.3 | Batch process images            | IMPL     | —   | ---    | ---           |
| US-2b.1 | Label card receipt (EUR)        | IMPL     | yes | G:real | ---           |
| US-2b.2 | Label cash receipt              | IMPL     | yes | ---    | ---           |
| US-2b.3 | Label foreign-currency receipt  | IMPL     | yes | ---    | ---           |
| US-2b.4 | Label split-payment receipt     | IMPL     | yes | ---    | ---           |
| US-2b.5 | Label receipt with returns      | IMPL     | yes | ---    | ---           |
| US-2b.6 | AI suggestions during labelling | IMPL     | —   | ---    | ---           |
| US-2b.7 | Edit existing label             | IMPL     | —   | G:real | ---           |
| US-2b.8 | Automated AI labelling          | NOT IMPL | —   | ---    | ---           |
| US-3.1  | Auto-match same currency        | IMPL     | yes | G:real | ---           |
| US-3.2  | Foreign currency match          | IMPL     | yes | ---    | ---           |
| US-3.3  | Widen date range                | IMPL     | yes | ---    | ---           |
| US-3.4  | Widen amount range              | IMPL     | yes | ---    | ---           |
| US-3.5  | Swap DD/MM                      | IMPL     | yes | ---    | ---           |
| US-3.6  | Disambiguate 2-14 matches       | IMPL     | yes | ---    | ---           |
| US-3.7  | Too many matches (15+)          | IMPL     | yes | ---    | ---           |
| US-3.8  | Correct receipt inline          | IMPL     | yes | ---    | ---           |
| US-3.9  | Direct asset purchase (gold)    | IMPL     | yes | ---    | ---           |
| US-3.10 | Skip cash-only receipt          | IMPL     | yes | ---    | ---           |
| US-3.11 | Withdrawal + fees               | NOT IMPL | yes | ---    | ---           |
| US-3.12 | Multi txn same account          | WONTFIX  | —   | ---    | ---           |
| US-3.13 | Foreign currency + returns      | NOT IMPL | —   | ---    | ---           |
| US-3.14 | Duplicate blocked               | IMPL     | yes | ---    | ---           |
| US-3.15 | Verify data up to date          | NOT IMPL | —   | ---    | ---           |
| US-4.1  | Full pipeline                   | IMPL     | yes | G:real | T:e           |
| US-4.2  | Randomised data for demos       | IMPL     | —   | ---    | ---           |
| US-4.3  | Generate .rules files           | IMPL     | —   | ---    | ---           |
| US-4.4  | Incremental pipeline            | NOT IMPL | —   | ---    | ---           |
| US-4.5  | Opening balances                | IMPL     | —   | ---    | ---           |
| US-5.1  | Sankey diagram                  | IMPL     | yes | G:fake | ---           |
| US-5.2  | Treemap plot                    | IMPL     | yes | G:fake | ---           |
| US-5.3  | Dash dashboard                  | IMPL     | —   | ---    | ---           |
| US-C.1  | Rule-based classification       | IMPL     | yes | ---    | T:u (partial) |
| US-X.2  | Reproducible pipeline           | IMPL     | —   | ---    | ---           |
| US-X.4  | Unique transaction hashes       | IMPL     | —   | ---    | ---           |
| US-X.5  | GIFs from integration tests     | IMPL     | —   | G:real | T:e           |
| US-X.6  | 1 image per receipt             | IMPL     | yes | ---    | ---           |

**Key gap**: The matching algorithm (Step 3) has 15 user stories and **zero dedicated tests**. This is the highest-risk area.

______________________________________________________________________

## 3. Visualization Suggestion

### A. Coverage Overlay on DAG

Extend `generate_userstory_artifacts.py` to emit a **test coverage DAG**:

- Green edges = story has unit + integration test
- Yellow edges = story has only E2E/GIF test
- Red edges = story has no test
- Grey edges = NOT YET IMPLEMENTED

Add a `test_coverage` field to each story in `userstory_dag_data.yaml`:

```yaml
- id: US-3.1
  test_coverage:
    unit: [test_matching_skip_logic.py]
    integration: [test_matching_auto_link.py]
    e2e: [test_gif_3_match_receipt_to_csv.py]
```

Generate `dag_test_coverage.puml` alongside existing artifacts.

### B. Auto-Generated Coverage Matrix

Generate `user_stories/dag/output/coverage_matrix.md` from the YAML — the table
in section 2 above, but auto-generated so it never goes stale.

______________________________________________________________________

## 4. Prioritized Test Plan

### P0 — Core Data Flow (happy path through the DAG)

| #   | Story   | Type        | What to Assert                                                                    |
| --- | ------- | ----------- | --------------------------------------------------------------------------------- |
| 1   | US-1a.1 | Integration | Load `1_bank_1_wallet.yaml` → Config has correct accounts, CSV mapping, dir paths |
| 2   | US-1b.1 | Unit        | Load categories.yaml → nested dict → flattened paths (`groceries:ekoplaza`)       |
| 3   | US-2b.1 | Integration | Create receipt label JSON → validate schema, hash, bidirectional image↔label      |
| 4   | US-3.1  | Integration | Receipt (42.17 EUR, Jan 15) + CSV (42.17 EUR, Jan 15) → auto-link, 1 match        |
| 5   | US-3.10 | Unit        | Wallet receipt (no CSV) → matcher returns SKIP outcome                            |
| 6   | US-C.1  | Unit        | "ekoplaza" in description → classifies as `groceries:ekoplaza`                    |
| 7   | US-4.1  | E2E         | Full pipeline → journal exists, postings balanced, correct accounts               |
| 8   | US-X.4  | Unit        | Same transaction → same hash; different transaction → different hash              |

### P1 — Matching Algorithm Edge Cases (highest-risk untested area)

| #   | Story   | Type        | What to Assert                                                            |
| --- | ------- | ----------- | ------------------------------------------------------------------------- |
| 9   | US-1a.2 | Integration | Multi-bank config → separate import dirs, both in journal                 |
| 10  | US-1a.3 | Integration | Wallet account has no CSV → config loads, wallet receipts skip matching   |
| 11  | US-3.2  | Integration | GBP receipt + EUR CSV → currency convert → match at 100\*1.175=117.50 EUR |
| 12  | US-3.3  | Integration | Receipt Jan 15, CSV Jan 18 → no match ±2d → widen ±5d → match             |
| 13  | US-3.4  | Integration | Receipt 49.99, CSV 50.00 → no exact match → widen ±0.02 → match           |
| 14  | US-3.5  | Integration | Date 01-05-2025 wrong → swap DD/MM → match                                |
| 15  | US-3.6  | Integration | 3 candidates → ranked by weighted score → correct ordering                |
| 16  | US-3.14 | Integration | Link receipt → re-link same CSV → SystemError raised                      |
| 17  | US-2b.2 | Integration | Cash receipt → wallet account → label JSON has wallet reference           |
| 18  | US-2b.4 | Integration | Split payment (30 card + 20 cash) → 2 account_transactions                |
| 19  | US-2b.5 | Integration | Bought 3, returned 1 → net amount = bought - returned                     |
| 20  | US-1b.3 | Integration | Salary credit → classified as income:salary (not expense)                 |

### P2 — Extended Scenarios & Cross-Cutting

| #   | Story   | Type        | What to Assert                                                    |
| --- | ------- | ----------- | ----------------------------------------------------------------- |
| 21  | US-3.7  | Integration | Wide params → 15+ matches → TOO_MANY outcome                      |
| 22  | US-3.8  | Integration | Correct receipt inline → matcher retries with updated data        |
| 23  | US-3.9  | Integration | Gold purchase → GRAMS → asset conversion → Assets:Gold            |
| 24  | US-1a.4 | Integration | Crypto config → loads without error, correct base currency        |
| 25  | US-1a.5 | Integration | Per-bank matching params override global defaults                 |
| 26  | US-X.2  | E2E         | Run pipeline twice → diff journal → identical                     |
| 27  | US-X.6  | Unit        | Two labels same image → error/warning                             |
| 28  | US-1b.2 | Integration | Add new category → existing labels still valid                    |
| 29  | US-5.1  | E2E         | Journal → Sankey SVG exists (test only structure, NOT fake data)  |
| 30  | US-5.2  | E2E         | Journal → Treemap SVG exists (test only structure, NOT fake data) |

______________________________________________________________________

## 5. GIF Plan: New GIFs to Create

All new GIFs follow the real-output pattern. Each GIF records the actual CLI
running against a temporary test environment.

### GIF Recording Pattern (mandatory for all new GIFs)

```python
# 1. Create temp test environment with real fixtures
env = setup_test_environment(config_template="1_bank_1_wallet.yaml")

# 2. Seed real data (receipt images, labels, bank CSV)
seed_receipts_into_root(config=env["config"], source_json_paths=[...])

# 3. Run real CLI command (no simulation)
navigator = TuiNavigator(
    command=f"hledger_preprocessor --config {env['config_path']} --link-receipts-to-transactions",
    dimensions=(38, 100),
)

# 4. Drive TUI with pexpect (for urwid-based interfaces)
navigator.wait_for("Select receipt")
navigator.press_down()
navigator.press_enter()

# 5. asciinema records everything → post-process → themed GIFs
```

### New GIFs by Priority

#### P0 GIFs (demonstrate core workflow, build on existing GIF dirs)

| GIF                             | Story  | Demo Script to Create                 | Records                                                                                    |
| ------------------------------- | ------ | ------------------------------------- | ------------------------------------------------------------------------------------------ |
| `3b_foreign_currency_match.gif` | US-3.2 | `real_foreign_currency_match_demo.py` | `--link-receipts-to-transactions` with GBP receipt vs EUR CSV, user enters conversion rate |

This is the **single most valuable new GIF** — it shows the currency conversion
TUI flow which is the most complex user-facing matching feature.

#### P1 GIFs (matching edge cases — only if TUI interaction is involved)

| GIF                          | Story   | Demo Script                 | Records                                                                        |
| ---------------------------- | ------- | --------------------------- | ------------------------------------------------------------------------------ |
| `3c_widen_date_match.gif`    | US-3.3  | `real_widen_date_demo.py`   | `--link-receipts-to-transactions` with delayed posting, user widens date range |
| `3d_disambiguate_match.gif`  | US-3.6  | `real_disambiguate_demo.py` | `--link-receipts-to-transactions` with 3 candidates, user selects correct one  |
| `2b_label_cash_receipt.gif`  | US-2b.2 | extend `receipt_editor.py`  | `--edit-receipt` with cash wallet selection                                    |
| `2b_label_split_payment.gif` | US-2b.4 | extend `receipt_editor.py`  | `--edit-receipt` with 2 account transactions                                   |

#### Not Planned as GIFs (tested via unit/integration tests only)

These stories have **no user-visible TUI interaction** worth recording:

- US-3.10 (skip cash receipt — automatic, no TUI)
- US-3.14 (duplicate blocked — error case)
- US-X.4 (hash uniqueness — internal logic)
- US-C.1 (rule classification — internal logic)

______________________________________________________________________

## 6. Test File Structure

```
test/
├── conftest.py                              # EXISTING session-scoped temp_finance_root
│
├── unit/
│   ├── __init__.py                          # EXISTING
│   ├── test_hledger_dict.py                 # EXISTING
│   ├── test_classification.py               # EXISTING
│   ├── test_category_loading.py             # NEW: US-1b.1
│   ├── test_transaction_hash.py             # NEW: US-X.4
│   ├── test_receipt_schema.py               # NEW: US-2b.1
│   ├── test_net_amount_calculation.py       # NEW: US-2b.5
│   ├── test_currency_conversion.py          # NEW: US-3.2 math
│   └── test_matching_skip_logic.py          # NEW: US-3.10
│
├── integration/
│   ├── __init__.py                          # EXISTING
│   ├── test_config_loading.py               # EXISTING (extend for US-1a.2, 1a.3, 1a.4)
│   ├── test_hledger_postings.py             # EXISTING
│   ├── test_new_flow.py                     # EXISTING (refactor to pytest)
│   ├── test_receipt_labelling.py            # NEW: US-2b.1/2/3/4/5
│   ├── test_matching_auto_link.py           # NEW: US-3.1
│   ├── test_matching_foreign_currency.py    # NEW: US-3.2
│   ├── test_matching_widen_date.py          # NEW: US-3.3
│   ├── test_matching_widen_amount.py        # NEW: US-3.4
│   ├── test_matching_swap_ddmm.py           # NEW: US-3.5
│   ├── test_matching_disambiguate.py        # NEW: US-3.6
│   ├── test_matching_too_many.py            # NEW: US-3.7
│   ├── test_matching_correct_inline.py      # NEW: US-3.8
│   ├── test_matching_asset_purchase.py      # NEW: US-3.9
│   ├── test_matching_duplicate_blocked.py   # NEW: US-3.14
│   ├── test_split_payment.py               # NEW: US-2b.4
│   └── test_income_classification.py        # NEW: US-1b.3
│
├── e2e/
│   ├── __init__.py                          # EXISTING
│   ├── gif_test_helpers.py                  # EXISTING
│   ├── test_fixtures.py                     # EXISTING
│   ├── test_start_sh.py                     # EXISTING
│   ├── test_gif_*.py                        # EXISTING (7 files)
│   ├── test_pipeline_reproducibility.py     # NEW: US-X.2
│   └── test_pipeline_journal_correctness.py # NEW: US-4.1 assertions
│
├── fixtures/
│   ├── categories/
│   │   └── example_categories.yaml          # EXISTING
│   ├── config_templates/
│   │   ├── 1_bank_1_wallet.yaml             # EXISTING
│   │   ├── 1_bank_5_assets.yaml             # EXISTING
│   │   ├── 2_banks_1_wallet.yaml            # NEW: US-1a.2
│   │   └── 1_bank_crypto.yaml              # NEW: US-1a.4
│   ├── postings/                            # EXISTING
│   ├── receipts/
│   │   ├── groceries_ekoplaza.json          # EXISTING
│   │   ├── groceries_ekoplaza_card.json     # EXISTING
│   │   ├── repairs_bike.json                # EXISTING
│   │   ├── dummy_receipt.jpg                # EXISTING
│   │   ├── coffee_cash.json                 # NEW: US-2b.2
│   │   ├── atm_london_gbp.json             # NEW: US-3.2
│   │   ├── split_dinner.json               # NEW: US-2b.4
│   │   ├── return_item.json                # NEW: US-2b.5
│   │   ├── delayed_shop.json               # NEW: US-3.3
│   │   ├── rounded_shop.json               # NEW: US-3.4
│   │   └── gold_dealer.json                # NEW: US-3.9
│   └── csv_transactions/                    # NEW directory
│       ├── triodos_basic.csv               # 1 Ekoplaza row (US-3.1)
│       ├── triodos_ambiguous.csv           # 3 similar rows (US-3.6)
│       ├── triodos_delayed.csv             # Posted 3 days late (US-3.3)
│       ├── triodos_rounded.csv             # Bank-rounded amount (US-3.4)
│       ├── triodos_foreign_atm.csv         # ATM withdrawal in EUR (US-3.2)
│       └── triodos_swapped_date.csv        # DD/MM ambiguous (US-3.5)
│
└── helpers/
    ├── __init__.py                          # EXISTING
    ├── assertions.py                        # EXISTING (extend with journal assertions)
    ├── generators.py                        # EXISTING
    └── seeders.py                           # EXISTING (extend for new receipt types)
```

**Totals: 18 new test files, 12 new fixture files, 5 new GIF demo scripts.**

______________________________________________________________________

## 7. Implementation Order

### Phase 1: P0 Unit Tests (no external deps needed)

1. `test_category_loading.py`
1. `test_transaction_hash.py`
1. `test_receipt_schema.py`
1. `test_net_amount_calculation.py`
1. `test_matching_skip_logic.py`

### Phase 2: P0 Integration Tests (use temp_finance_root)

6. Extend `test_config_loading.py` for multi-bank
1. `test_matching_auto_link.py`
1. `test_receipt_labelling.py`

### Phase 3: P0 E2E Tests

9. `test_pipeline_journal_correctness.py`

### Phase 4: P1 Matching Integration Tests

10. `test_matching_foreign_currency.py`
01. `test_matching_widen_date.py`
01. `test_matching_widen_amount.py`
01. `test_matching_swap_ddmm.py`
01. `test_matching_disambiguate.py`
01. `test_matching_duplicate_blocked.py`

### Phase 5: P1 GIF Demos (real output only)

16. `real_foreign_currency_match_demo.py` + `generate.sh`
01. `real_widen_date_demo.py` + `generate.sh`
01. `real_disambiguate_demo.py` + `generate.sh`

### Phase 6: P2 Extended Tests

19-30. Remaining P2 tests as capacity allows.

______________________________________________________________________

## 8. Fixture Data Design

All fixture data matches the DAG node definitions in `userstory_dag_data.yaml`.
Receipt JSONs follow the exact schema of existing fixtures
(`groceries_ekoplaza_card.json`, `repairs_bike.json`).

### Key Test Data Relationships

```
cfg_1b1w + cat_basic + match_default + start_2024_1000eur
  ├── csv_ekoplaza_4217_jan15 + img_ekoplaza_card → lbl_ekoplaza_card_eur → AUTO_LINK (US-3.1)
  ├── csv_delayed_jan18 + img_delayed_shop → lbl_delayed_shop → WIDEN_DATE (US-3.3)
  ├── csv_rounded_5000 + img_rounded_shop → lbl_rounded_shop → WIDEN_AMOUNT (US-3.4)
  ├── img_coffee_cash → lbl_coffee_cash → SKIP (US-3.10)
  └── csv_ekoplaza_4217_jan15 (already linked) → BLOCKED (US-3.14)

cfg_1b5a + cat_basic + match_default + start_2024_1000eur
  └── csv_atm_gbp_11750 + img_atm_gbp → lbl_atm_100gbp → CURRENCY_CONVERT (US-3.2)
```

Each fixture CSV, receipt JSON, and config YAML is a materialization of the
corresponding DAG node, ensuring tests exercise the exact paths defined in the
user story specifications.

______________________________________________________________________

## 9. User-Facing Documentation Site (GitHub Pages)

### Problem

GitHub README only supports auto-looping GIFs — users cannot pause, scrub, or
control playback speed. Manual video upload is not acceptable (CI/CD must
auto-update). Users need both **overview** (where am I in the workflow?) and
**detail** (let me study this step).

### Solution: Static GitHub Pages Site with `<video>` Tags

The MP4 files already exist (generated by `common.sh` via ffmpeg alongside every
GIF). HTML `<video controls>` gives native pause/scrub/speed for free.

### Architecture

```
README.md (GitHub repo)
  └── Auto-looping GIFs for quick overview (existing, unchanged)
  └── Link: "Interactive demos with pause/scrub: <pages-url>"

gh-pages branch (GitHub Pages)
  └── index.html — static site generated from userstory_dag_data.yaml
       ├── Landing: clickable SVG DAG (full pipeline overview)
       ├── Sidebar: stories grouped by step (1a, 1b, 2a, 2b, 3, 4, 5)
       └── Per-story page:
            ├── <video controls loop> of the MP4
            ├── Isolated DAG diagram (from existing isolated/*.png)
            ├── Acceptance criteria (from YAML)
            └── Previous / Next navigation
```

### Two Navigation Modes

**Overview mode** — Interactive DAG (`dag_all_stories.png` rendered as clickable
SVG). Each node/edge links to its story page. User sees the full pipeline at a
glance and clicks to drill in.

**Story mode** — Single story page:

- `<video controls loop>` — pause, scrub, adjust speed
- Isolated DAG showing just this story's path (already generated)
- Acceptance criteria checklist (from YAML `acceptance_criteria` field)
- Previous / Next links following DAG topological order

### Files to Create

| File                                  | Purpose                                    |
| ------------------------------------- | ------------------------------------------ |
| `user_stories/dag/generate_site.py`   | Reads YAML + copies MP4s → emits HTML site |
| `user_stories/dag/site_template.html` | HTML template (f-string or Jinja2)         |
| `.github/workflows/docs.yml`          | Auto-deploy Pages on push                  |

### `generate_site.py` (~200 lines)

Reads `userstory_dag_data.yaml`, generates a static HTML site:

```python
# Pseudocode
stories = load_yaml("userstory_dag_data.yaml")["stories"]

for story in stories:
    # Map story to its MP4 and isolated DAG PNG
    mp4 = find_mp4_for_story(story["id"])  # from gifs/*/output/
    dag_png = f"output/isolated/{story_id}.png"  # already exists

    emit_html_page(
        story=story,
        video_src=mp4,
        dag_src=dag_png,
        acceptance_criteria=story["acceptance_criteria"],
        prev_story=prev,
        next_story=next,
    )

emit_index_page(
    dag_svg="output/dag_all_stories.svg",  # clickable overview
    story_links=all_story_links,
)
```

No heavy framework needed. The data source is already structured.

### CI/CD Auto-Deploy

```yaml
# .github/workflows/docs.yml
name: Deploy User Story Docs
on:
  push:
    paths: ['gifs/**', 'user_stories/**']
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: python user_stories/dag/generate_site.py --output site/
      - uses: peaceiris/actions-gh-pages@v3
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          publish_dir: ./site
```

Triggers on any change to GIF demos or user stories — site always reflects
current code.

### Why Not MkDocs / Sphinx / etc.?

The data source (`userstory_dag_data.yaml`) already has all metadata. A single
Python script that emits HTML + copies MP4s is simpler, faster, and has zero
extra dependencies beyond what the project already uses (PyYAML, Jinja2 or
f-strings).

### Changes to Existing Repo

| What                                  | Change                                   |
| ------------------------------------- | ---------------------------------------- |
| `README.md`                           | Add link to Pages site                   |
| `user_stories/dag/generate_site.py`   | NEW: reads YAML, emits HTML site         |
| `user_stories/dag/site_template.html` | NEW: page template                       |
| `.github/workflows/docs.yml`          | NEW: auto-deploy on push                 |
| `gifs/*/output/*.mp4`                 | Already exist — copied to site by script |
