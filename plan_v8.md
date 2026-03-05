# Plan v8.C — Fix US-2b.1 Full Path GIF Generation

## Problem Summary

Two issues with the US-2b.1 receipt labelling demo GIF:

1. **Missing config & categorisation steps**: The full-path GIF only showed
   the receipt editing TUI. It should show config → categories → receipt
   labelling.
1. **pexpect EOF at receipt_editor.py line 190**: After saving, the script
   waited for `"EXPORTING to:"` but the TUI exits (verbose=False skips that
   prompt), causing EOF.

## Solution

### Fix A: receipt_editor.py + tui_navigator.py

- `tui_navigator.py`: Added `pexpect.EOF` catch in `wait_for()` when
  `silent=True` — returns `False` instead of crashing.
- `receipt_editor.py`: Removed dead `wait_for("EXPORTING to:")` block,
  replaced with `wait_for_exit(timeout=15)`.

### Fix B: Full-path video via MP4 stitching

Instead of re-recording a new combined demo, **stitch existing segment
videos** using ffmpeg:

```
cfg_1b1w.mp4  (US-1a config: 1 bank + 1 wallet)  74.7s
  + cat_basic.mp4  (US-1b categories)               5.5s
  + 2b_label_receipt_dracula.mp4  (receipt TUI)     31.9s
  = 2b1_full_path.mp4                              112.1s
```

Sidecar marker JSONs are merged with time offsets into
`2b1_full_path_markers.json` (16 markers from config through receipt label).

### Fix C: Wiring

- Added `gif_video: 2b1_full_path` to US-2b.1 in `userstory_dag_data.yaml`
- `generate_site.py` discovers it and embeds the offset timestamps

## Files Changed

| File                                       | Change                                 |
| ------------------------------------------ | -------------------------------------- |
| `gifs/automation/tui_navigator.py`         | EOF handling in `wait_for()`           |
| `gifs/automation/receipt_editor.py`        | Remove dead EXPORTING wait             |
| `gifs/automation/stitch_full_path.py`      | **New** — ffmpeg concat + marker merge |
| `user_stories/dag/userstory_dag_data.yaml` | `gif_video: 2b1_full_path` on US-2b.1  |

## Commands

```bash
# 1. Regenerate all GIFs (including 2b segment + stitch)
conda run -n hledger_preprocessor python -m pytest test/e2e/test_gif_2b_label_receipt.py -xvs && \
python -m gifs.automation.stitch_full_path \
    --segments \
        gifs/1a_setup_config/output/cfg_1b1w.mp4 \
        gifs/1b_add_category/output/cat_basic.mp4 \
        gifs/2b_label_receipt/output/2b_label_receipt_dracula.mp4 \
    --output gifs/2b_label_receipt/output/2b1_full_path.mp4

# 2. Build and serve the site
./build_userstories.sh --site --serve
```
