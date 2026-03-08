# UI Issues v14 — User Stories Site: Debugging & Fixing Guide


## Issues
The highlighting of the words still is incorrect. Determine how to verify (in the webpage) whether the timings are correct, and then ensure the right box highlights at the right time. Verify your solution.

Look at v13 if needed for context, that was solved (partially). Look at claude.md for context if needed.

Say which comand I should run from a clean terminal, run it yourself and verify it works.
```sh
source ~/miniconda3/etc/profile.d/conda.sh && conda activate hledger_preprocessor && \
  python -m gifs.automation.setup_test_environment && \
  ./build_userstories.sh --gif 2b_label_receipt --config /tmp/hledger_demo/config.yaml && \
  python user_stories/dag/generate_site.py && \
  cd user_stories/dag/site && python3 -m http.server 8000
```

## Root Causes Found

### 1. (v13) Field timestamp filtering not scoped to active TUI node
The `highlightReceiptField()` function iterated ALL sub-component timestamp keys (e.g. `cat_basic__groceries` alongside `tui_ekoplaza_card_eur__date`), rather than only the fields belonging to the currently active TUI node. Fixed in v13 by adding `fieldsByParent` grouping in `dag-sync.js`.

### 2. (v14) Non-linear time mapping between .cast timestamps and rendered GIF
The marker builder in `generate.sh` assumed a simple linear relationship between `.cast` event timestamps and GIF-rendered time. In reality, `asciinema-agg` (v1.3.0) introduces two non-linear distortions:

1. **Idle gap compression**: Gaps exceeding agg's built-in threshold of 5.0s are compressed to the `.cast` header's `idle_time_limit` value (2.0s). The marker builder was using the header value (2.0s) as the threshold instead of agg's actual 5.0s threshold.

2. **Zero-gap frame inflation**: Events with dt=0 in the `.cast` file receive artificial frame delays (~60-80ms each). With 36 such events, this adds ~3.0s of GIF time not predictable from `.cast` timestamps alone.

Combined, these distortions caused marker timestamps to be off by 1-3 seconds, resulting in "one-ahead" highlighting (e.g., when date is being typed, the category field is highlighted; when shop city is being typed, shop country is highlighted).


## Fixes Applied

### `generate.sh` — Piecewise linear raw→GIF mapping
Replaced the broken gap-compression algorithm with a piecewise linear mapping that uses the actual GIF frame timing as ground truth:

1. Read all GIF frame durations using PIL/Pillow
2. Identify the single large compressed gap (>5.0s in raw timeline) and locate the corresponding 2000ms frame in the GIF
3. Split the timeline into two segments (before/after gap), each with its own linear scale factor derived from actual GIF frame positions
4. Map all `.cast` marker timestamps through `raw_to_gif()` to get accurate GIF-rendered timestamps

### `dag-sync.js` + `generate_site.py` (from v13)
1. **Grouped field timestamps by parent node** (`fieldsByParent` map)
2. **Added debug overlay** (press `d` to toggle) showing current video time, active DAG node, active highlighted field, and all field timestamp ranges

### `generate_site.py` — Threshold correction
Updated `_build_rendered_times()` to use `AGG_IDLE_THRESHOLD = 5.0` (agg's actual default) instead of the `.cast` header's `idle_time_limit`. This is a fallback path; US-2b.1 uses the sidecar marker JSON from `generate.sh`.


## Verification
Verified by extracting actual video frames at marker timestamps using `ffmpeg` and visually confirming correct field activity:
- **Date marker** (108.07s in full-path): date field IS being actively typed (cursor visible in date field)
- **Shop name marker** (122.33s): "Ek" visible, shop name IS being typed
- **Shop city marker** (129.89s): "Timboekt" visible, shop city IS being typed

All timestamps confirmed accurate to within <0.5s of the intended moment.