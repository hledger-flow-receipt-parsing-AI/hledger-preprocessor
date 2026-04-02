# GIF Demo Generation

## Directory Structure

Each user story has a GIF demo under `gifs/<name>/`:
- `generate.sh` — orchestrates recording, GIF generation, MP4 conversion, stitching
- `recordings/` — `.cast` files (asciinema recordings)
- `output/` — `.gif`, `.mp4`, `_markers.json`

Demo directories: `1a_setup_config`, `1b_add_category`, `2a_crop_receipt`, `2b_label_receipt`, `2b_label_foreign_currency`, `2b_label_split_payment`, `2b_label_returned_items`, `3_match_receipt_to_csv`, `3b_foreign_currency_match`, `3c_widen_date_match`, `3d_disambiguate_match`, `4_run_pipeline`, `5_show_plots`

## Build Commands

```bash
# Set up demo environment first
python -m gifs.automation.setup_test_environment

# Record a single GIF + rebuild site + serve
./build_userstories.sh --gif <name> --site --serve --config /tmp/hledger_demo/config.yaml

# Record all GIFs
./build_userstories.sh --gifs

# Just rebuild and serve the website (no re-record)
./build_userstories.sh --site --serve
```

## Recording Flow

1. `generate.sh` calls `run_full_pipeline` (from `scripts/common.sh`) which runs a Python automation module under `asciinema rec` → `.cast`
2. `.cast` post-processed by `gifs/automation/cast_postprocess.py` (timing fixes)
3. `asciinema-agg` converts `.cast` → `.gif`, then `ffmpeg` → `.mp4`
4. Markers extracted from `.cast` events into `_markers.json`

## Stitching

Some stories combine segments from multiple GIF demos into a "full-path" video. Done by `python -m gifs.automation.stitch_full_path`.

Rebuilding a child GIF (e.g. `3b_foreign_currency_match`) requires also rebuilding the parent that stitches it (e.g. `2b_label_foreign_currency`).

## Website

`user_stories/dag/generate_site.py` generates HTML site from `user_stories/dag/stories.yaml`. Output to `/tmp/site/`, served on port 8059.

## Automation Modules (`gifs/automation/`)

- `real_label_*_tui_demo.py` — drive urwid TUI receipt labeller via simulated input
- `real_*_match_demo.py` — drive matching flow
- `receipt_editor.py` — demo receipt values
- `cast_postprocess.py` — `.cast` timing/cleanup
- `stitch_full_path.py` — concatenate segment MP4s
