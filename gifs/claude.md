# GIF Demo Generation

## Overview

This directory contains scripts and automation for generating demonstration GIFs of hledger-preprocessor functionality.

## Directory Structure

- `1a_setup_config/` - Config file setup demo
- `1b_add_category/` - Adding spending categories
- `2a_crop_receipt/` - **Receipt image cropping TUI** (uses OpenCV)
- `2b_label_receipt/` - Receipt labeling TUI
- `2b_label_foreign_currency/` - Foreign-currency receipt labelling
- `2b_label_split_payment/` - Split-payment receipt labelling
- `2b_label_returned_items/` - Returned-items receipt labelling
- `3_match_receipt_to_csv/` - Matching receipts to bank transactions
- `3b_foreign_currency_match/` - Foreign-currency matching
- `3c_widen_date_match/` - Widen-date matching
- `3d_disambiguate_match/` - Disambiguation matching
- `4_run_pipeline/` - Full pipeline execution
- `5_show_plots/` - Financial visualization/plots
- `automation/` - Shared automation code and simulated demos
- `scripts/` - Common shell utilities
- `assets/` - Receipt images and other static assets

## Key Files

- `gif_config.yaml` - Configuration for GIF generation
- `scripts/common.sh` - Shared bash utilities for demos

## How GIFs and the User Stories Website Work

### Architecture

Each user story (e.g. US-2b.3) has a corresponding GIF demo that records the feature in action. The website at `http://localhost:8059/` displays these demos alongside DAG diagrams showing the data flow.

### Build entry point

Everything is driven by `build_userstories.sh` in the project root:
```bash
./build_userstories.sh --gif <name>    # Record a single GIF (e.g. 2b_label_foreign_currency)
./build_userstories.sh --gifs          # Record all GIFs
./build_userstories.sh --site          # Generate the HTML site from existing GIFs
./build_userstories.sh --site --serve  # Generate + serve on port 8059
./build_userstories.sh --gif <name> --site --serve  # Record GIF + rebuild site + serve
```

Before recording, set up the demo environment:
```bash
python -m gifs.automation.setup_test_environment
```
This creates `/tmp/hledger_demo/` with a config, CSV, journal, and categories.

### Per-GIF structure

Each `gifs/<name>/` directory contains:
- `generate.sh` — Orchestrates recording, GIF generation, MP4 conversion, and stitching
- `recordings/` — `.cast` files (asciinema recordings)
- `output/` — `.gif`, `.mp4`, and `_markers.json` files

### Recording flow

1. `generate.sh` calls `run_full_pipeline` (from `scripts/common.sh`) which runs a Python automation module (e.g. `gifs.automation.real_label_foreign_currency_tui_demo`) under `asciinema rec` to produce a `.cast` file
2. The `.cast` is post-processed (`gifs/automation/cast_postprocess.py`) to fix timing
3. `asciinema-agg` converts `.cast` → `.gif`, then `ffmpeg` converts `.gif` → `.mp4`
4. Markers are extracted from `.cast` events into a `_markers.json` sidecar for the website player

### Stitching (full-path videos)

Some stories require a "full-path" video combining multiple segments. For example, US-2b.3's full path is: config → categories → journal → CSV → receipt labelling → matching → journal output. Each segment is a separate `.mp4` from a different GIF demo.

Stitching is done at the end of a story's `generate.sh` via `python -m gifs.automation.stitch_full_path`. It concatenates segment MP4s and merges their marker JSONs.

**Important**: `./build_userstories.sh --gif 3b_foreign_currency_match` only runs the 3b script. If the parent story (e.g. `2b_label_foreign_currency`) stitches 3b into its full-path video, you must also rebuild the parent: `./build_userstories.sh --gif 2b_label_foreign_currency`.

### Website generation

`user_stories/dag/generate_site.py` generates the static HTML site:
- Reads story definitions from `user_stories/dag/stories.yaml`
- Generates SVG DAG diagrams (two-column layout: config left, receipt/matching right)
- Embeds GIF/MP4 players with marker-based chapter navigation
- Output goes to `/tmp/site/`

### Automation modules

`gifs/automation/` contains the Python scripts that drive each demo:
- `real_label_*_tui_demo.py` — Drive the urwid TUI receipt labeller via simulated input
- `real_*_match_demo.py` — Drive the matching flow
- `receipt_editor.py` — Defines demo receipt values (amounts, accounts, currencies)
- `cast_postprocess.py` — Post-processes `.cast` files (timing, cleanup)
- `stitch_full_path.py` — Stitches segment MP4s into full-path composites

## Cropping TUI Implementation

The actual cropping interface is at:
`src/hledger_preprocessor/receipts_to_objects/edit_images/crop_image.py`

It uses:

- OpenCV (`cv2`) for image display and drawing
- Green rectangle for crop boundaries
- Red crosshair for active corner indicator
- Arrow keys (10% steps), Alt (switch corners), Enter (save)
