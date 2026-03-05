# UI Issues — Story Site

## 1. cfg_1b1w has no GIF — 21 stories show interpolated timestamps

**Status: FIXED** — `generate.sh` already has the `cfg_1b1w` entry (lines 165-171)
but the script had not been re-run. Run `gifs/1a_setup_config/generate.sh` to
produce `cfg_1b1w.gif`, `cfg_1b1w.mp4`, and `cfg_1b1w_markers.json`.

**Affected stories:** US-1b.1, US-1b.3, US-2b.1–2b.5, US-3.1–3.11, US-3.14,
US-4.1, US-5.1, US-5.2, US-C.1.

## 2. Cast file @@NODE markers use old component IDs

**Status: FIXED** — replaced `cfg_1b1w__bank_csv` with `cfg_1b1w__triodos_csv`
and added `cfg_1b1w__eur_wallet` in
`gifs/3_match_receipt_to_csv/recordings/3_match_receipt_to_csv.cast`.

## 3. Step 3 stories show constant 3.45 s timestamps for early nodes

**Status: FIXED** — caused by issue #2 (old marker IDs). Now that the cast file
uses `cfg_1b1w__triodos_csv` and `cfg_1b1w__eur_wallet`, the sub-component chips
resolve to the correct 3.45 s timestamp (which is where those nodes actually
appear in the recording). The early nodes all appear at the same point because
the config/category/matching setup is shown as a single burst of markers.

## 4. Step 2b stories share one video — timestamps are evenly interpolated

**Status: OPEN** — `receipt_editor.py` does not call `emit_node_marker()` from
`gifs/automation/core/screen.py`. To fix, add `emit_node_marker()` calls at
the appropriate points in the demo flow (before the receipt list, before each
form field section). Then re-record to produce a cast file with `@@NODE`
markers and real timestamps.

## 5. cat_with_income GIF is missing the "freelance" segment

**Status: FIXED** — created `test/fixtures/config_fragments/categories/freelance.yaml`
and added the `freelance` segment to `gifs/1b_add_category/generate.sh`.
Run the script to regenerate the GIF with all 4 segments.

## 6. cat_extended has no GIF

**Status: FIXED** — created category fragment files (`transport.yaml`,
`dining.yaml`, `utilities.yaml`, `gold.yaml`, `silver.yaml`) and added a
`cat_extended` generation block to `gifs/1b_add_category/generate.sh`.
Run the script to generate `cat_extended.gif` and `cat_extended_markers.json`.

## 7. cfg_multi_bank is defined but unused

**Status: FIXED** — removed `cfg_multi_bank` from
`user_stories/dag/userstory_dag_data.yaml`. No story path referenced it.
Regenerate `.puml` files to remove it from DAG diagrams.

## 8. US-C.1 and US-X.6 have no video at all

**Status: OPEN** — both stories belong to sections with no GIF directory
(`Transaction Classification` and `Cross-cutting Concerns` map to `None` in
`SECTION_TO_GIF_DIR`). To fix, either:

- Create dedicated demo recordings for these sections, or
- Map their sections to existing GIF directories (US-C.1 shares a path
  structure with Step 3; US-X.6 spans Step 2b concerns).

## 9. Old GIF output files are not cleaned up

**Status: FIXED** — removed stale files from `gifs/1a_setup_config/output/`
(`01_setup_config.*`, `1a_setup_config.*`, `1a_setup_config_markers.json`) and
from `gifs/1b_add_category/output/` (`02_add_category.*`, `1b_add_category.*`,
`1b_add_category_markers.json`).

## 10. US-2b.3 and US-2b.4 reference cfg_1b5a and cat_extended but share the 2b video

**Status: OPEN** — these stories are in "Step 2b: Receipt Labelling" which maps
to `2b_label_receipt/` for video lookup, but the per-node GIFs (`cfg_1b5a`,
`cat_extended`) live in `1a_setup_config/` and `1b_add_category/` respectively.
The `gif_video` lookup is scoped to the story's own section directory. To fix,
either:

- Add a cross-section video lookup to `generate_site.py`, or
- Copy/symlink the relevant GIFs into `2b_label_receipt/output/`, or
- Add a `gif_video` field that supports cross-section references.

## 11. Step 4 and Step 5 stories have interpolated timestamps

**Status: OPEN** — same root cause as issue #4. `start_sh_demo.py` and
`show_plots_demo.py` do not call `emit_node_marker()`. Add marker calls at
the appropriate points in each demo flow, then re-record to produce cast files
with `@@NODE` markers.
