# Implementation Plan — ui-issues_v11.md

## Overview

Fix 5 groups of issues (A, B, C, D, E) for the US-2b.1 user story site page. All changes must use real data from src/tests — no faked/synthetic content.

---

## Issue A — Highlight receipt image when "Receipt Images" DAG box is highlighted

**Problem:** When the DAG node "Receipt Images / ekoplaza_card.jpg" is highlighted (during video playback or click), the receipt image in the page header isn't visually highlighted.

**Files to change:**
- `user_stories/dag/generate_site.py` — add a CSS class toggle on the receipt image pane when the `img_ekoplaza_card` node is active
- `user_stories/dag/site/assets/js/dag-sync.js` — in `highlightNode()`, detect when the active node is a receipt image node and add a highlight class to `.receipt-pane`
- `user_stories/dag/site/assets/css/style.css` — add `.receipt-pane.active` styling (glowing border, box-shadow with accent color)

**Approach:**
1. In `dag-sync.js`, when `highlightNode(nodeId)` is called and nodeId starts with `img_`, also add class `active` to the `.receipt-pane` element. Remove it when a different node is highlighted.
2. In `style.css`, add `.receipt-pane.active` with a `box-shadow: 0 0 12px var(--accent)` and `border-color: var(--accent)`.

---

## Issue B — Highlight receipt image regions during TUI field entry

**Problem:** When the TUI demo fills in each field (date, time, amount, shop, etc.), the corresponding area on the receipt image should be highlighted with a bounding box.

**Sub-issues:**
- B.1: date → highlight "Date: 2025-01-15" on receipt
- B.2: time → highlight "Time: 14:32" on receipt
- B.2.a: account → show payment method. **Requires adding card payment info to receipt image** (e.g., "Paid with: Card XXXX5342")
- B.2.b: Ensure config used for receipt labelling GIF matches the config from the config setup GIF (1 bank + 1 wallet: Triodos checking EUR + EUR physical wallet)
- B.3: currency (EUR) → highlight EUR on receipt
- B.4: amount (42.17) → highlight "EUR 42.17" total
- B.5: change (0) → annotate "(not on receipt)"
- B.6: shop name (Ekoplaza) → highlight "EKOPLAZA"
- B.7: street, house nr, zipcode, city → **Requires adding these to receipt image**
- B.8: country (NL) → highlight "NL" on receipt; tax → highlight tax line

### Step B.1 — Update receipt image generator to include missing fields

**Files to change:**
- `test/helpers/seeders.py` — `_create_receipt_image()` function

**Changes:**
1. Add **time** extraction: change `the_date[:10]` to also extract time from the ISO datetime and render `Time: HH:MM`
2. Add **payment method**: render `Paid with: Card` or `Paid with: Cash` based on account type. For card, add `Card: XXXX5342` (last 4 digits from account config or a fixed value)
3. Add **country**: render country from `address.country` (e.g., "NL" or "Belgie")
4. Add **street/house_nr/zipcode/city** — these are already rendered if present in the JSON fixture. The issue is the *static* `ekoplaza_card.png` in `gifs/assets/receipts/` was created separately. We need to regenerate it from the fixture data.
5. Add **tax line** — already rendered ("TAX (BTW)") if `total_tax > 0`

### Step B.2 — Regenerate the ekoplaza_card.png receipt image

**Files to change:**
- `gifs/assets/receipts/ekoplaza_card.png` — regenerate from fixture data
- Create a small script or add to existing build to regenerate the receipt PNG from `test/fixtures/receipts/groceries_ekoplaza_card.json` using the updated `_create_receipt_image()`

### Step B.3 — Define bounding box regions for each TUI field

**Files to change:**
- New data: add a `receipt_highlight_regions` section to `userstory_dag_data.yaml` OR create a sidecar JSON file (e.g., `gifs/assets/receipts/ekoplaza_card_regions.json`)

**Data structure:**
```json
{
  "date_time": {"x": 20, "y": 100, "w": 200, "h": 18, "label": "Date"},
  "time": {"x": 20, "y": 118, "w": 150, "h": 18, "label": "Time"},
  "shop_name": {"x": 50, "y": 15, "w": 200, "h": 22, "label": "Shop"},
  "amount": {"x": 160, "y": 265, "w": 120, "h": 20, "label": "Total"},
  "currency": {"x": 160, "y": 265, "w": 30, "h": 20, "label": "EUR"},
  "tax": {"x": 20, "y": 245, "w": 260, "h": 18, "label": "Tax"},
  "payment_method": {"x": 20, "y": 290, "w": 260, "h": 18, "label": "Payment"},
  ...
}
```

Exact coordinates will be determined after regenerating the receipt image.

### Step B.4 — Add SVG overlay for receipt highlighting

**Files to change:**
- `user_stories/dag/generate_site.py` — when generating story HTML, add an SVG overlay element on top of the receipt image, with rect elements for each region, initially hidden
- `user_stories/dag/site/assets/js/dag-sync.js` — extend the video sync to show/hide bounding boxes based on which TUI field is being filled. This maps marker timestamps to receipt regions.
- `user_stories/dag/site/assets/css/style.css` — style the SVG overlay rects (colored stroke, semi-transparent fill, animated appearance)

**Approach:**
1. The receipt image sits inside `.receipt-pane > .zoom-pane-inner`. Add an SVG overlay positioned absolutely on top of the image.
2. Each rect in the SVG has a `data-field` attribute (e.g., `data-field="date_time"`).
3. In the markers JSON for the receipt labelling segment, we already have timestamps for when each field starts being filled (from the `lbl_ekoplaza_card_eur__date_time`, `lbl_ekoplaza_card_eur__amount`, etc. component markers).
4. In `dag-sync.js`, during `timeupdate`, check if the current timestamp falls within a field's time range and show the corresponding bounding box on the receipt.

### Step B.5 — Ensure correct config is used for receipt labelling GIF

**Files to check/change:**
- `gifs/2b_label_receipt/generate.sh` — verify it uses the `1_bank_1_wallet.yaml` config template (Triodos checking EUR + EUR physical wallet)
- `test/conftest.py` — verify the fixture creates matching accounts
- If the config isn't correct, fix `generate.sh` to use the right config path

---

## Issue C — Fix cursor navigation for "Add another account (y/n)"

**Problem:** After entering "change returned", the cursor movement sequence is wrong. Currently:
1. Cursor goes to start of "Change returned" line (C)
2. Enter → cursor goes to middle of `( ) y`
3. Cursor goes to start `()`
4. Simultaneously `(X) n` gets filled and cursor moves to next question

**Expected (C.b):**
1. Cursor should go to middle of `( ) y` first
2. Then move to middle of `( ) n`
3. Then press enter → `( ) n` becomes `(X) n`
4. Cursor moves to next question

**Files to change:**
- `gifs/automation/receipt_editor.py` — `_select_horizontal_n()` and/or the sequence in `_fill_receipt_fields()` around Field 7

**Analysis:** The current `_select_horizontal_n()` sends `RIGHT` then `ENTER`. The issue might be:
- Missing pause after the `change` field's Enter before the horizontal selector renders
- The TUI might need an explicit wait for the y/n prompt to render before sending RIGHT
- May need to add `nav.wait_for("another account", timeout=5)` before sending RIGHT

**Approach:**
1. Add a `nav.wait_for()` call to wait for the "Add another account" prompt to appear
2. Add a brief pause so the cursor is visually seen on `( ) y` first
3. Then send `RIGHT` with a pause so cursor is seen on `( ) n`
4. Then send `ENTER`

---

## Issue D — Split "Receipt Labels (JSON)" into 3 sub-boxes

**Problem:** The current DAG has one "Receipt Labels (JSON)" box. It should be split into 3 layers inside an overarching dashed "Receipt Labelling" box (mirroring the Configuration group pattern).

The 3 sub-layers:
1. "Receipt Labelling — show initial receipt does not exist" (no label JSON yet)
2. "Label receipt in TUI, based on image" (the TUI labelling process)
3. "Receipt Labelling — show Receipt label output JSON" (resulting JSON)

**Files to change:**

### Step D.1 — Update YAML structure
- `user_stories/dag/userstory_dag_data.yaml`:
  - Replace the single `receipt_lbl` layer with 3 layers:
    - `receipt_lbl_before` — "No label exists yet"
    - `receipt_lbl_tui` — "Label receipt in TUI"
    - `receipt_lbl_after` — "Receipt label output JSON"
  - Move/split existing nodes across these 3 layers
  - Update story paths for US-2b.1 and any other stories referencing `receipt_lbl`

### Step D.2 — Add Receipt Labelling group to site generator
- `user_stories/dag/generate_userstory_artifacts.py`:
  - Add `RECEIPT_GROUP_LAYERS = {"receipt_lbl_before", "receipt_lbl_tui", "receipt_lbl_after"}`
  - Update `LAYER_ORDER` to include the 3 new layers (replacing the old single one)

- `user_stories/dag/generate_site.py`:
  - Mirror the `CONFIG_GROUP_LAYERS` / config group box pattern for `RECEIPT_GROUP_LAYERS`
  - In `generate_overview_svg_direct()`: track `receipt_y_start`, `receipt_y_end`, `receipt_max_right`, render a dashed box with label "Receipt Labelling"
  - In `generate_story_svg_direct()`: same pattern for story-specific SVGs

### Step D.3 — Update tests
- Any tests that reference `receipt_lbl` layer name or the old single-layer structure need updating

---

## Issue E — Replace fake matching with real src code execution

**Problem:** The matching demo in `match_receipt_demo.py` uses hardcoded/formatted output. It should call the actual matching src code and show the real CLI command + resulting diff.

**Files to change:**

### Step E.1 — Update match_receipt_demo.py
- `gifs/automation/match_receipt_demo.py`:
  - Instead of printing hardcoded matching steps, actually run:
    ```
    hledger_preprocessor --config <path> --link-receipts-to-transactions
    ```
  - Capture the receipt label JSON before and after matching
  - Show a diff of the two JSONs (before: no `csv_transaction` field; after: linked)
  - Use the test fixture setup (same config as other GIFs) to ensure real data

### Step E.2 — Update the matching GIF generation
- `gifs/2b_label_receipt/generate.sh` (or create a new `gifs/3_match_receipt/generate.sh`):
  - Record the matching demo using asciinema
  - The demo runs the real CLI command and shows the diff
  - Stitch into the full-path video

### Step E.3 — Verify matching works end-to-end
- Run the matching with the test fixture data:
  - Config: 1_bank_1_wallet.yaml
  - CSV: triodos_2025.csv (contains Jan 15, -42.17 EUR, Ekoplaza)
  - Receipt: groceries_ekoplaza_card.json (Jan 15, 42.17 EUR, Ekoplaza, Triodos)
  - Expected: 1 match found → auto-linked
- Verify the resulting receipt JSON contains the `csv_transaction` reference

---

## Execution Order

1. **B.1 + B.2** — Update receipt image generator & regenerate PNG (prerequisite for B.3-B.5)
2. **D** — Split DAG layers (structural change, do early to avoid conflicts)
3. **C** — Fix cursor navigation (isolated change in receipt_editor.py)
4. **B.5** — Verify/fix config used for GIF generation
5. **E** — Replace fake matching with real code
6. **A** — Receipt highlight on DAG hover (simple JS/CSS)
7. **B.3 + B.4** — Bounding box regions + SVG overlay (depends on new receipt image)
8. **Regenerate all GIFs** — `./build_userstories.sh` with updated code
9. **Final verification** — Rebuild site, check all pages, verify no regressions

---

## Constraints (from the issue doc)

- No faked data, no synthetic videos
- Regenerate GIFs from src + test functionalities
- If YAML is updated, tests must be updated too
- Ensure data fixtures (journal output, starting journal, bank CSV) exist and work
- Can disable theme variants and just use 1 theme for efficiency
- Everything must be reproducible
