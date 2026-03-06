# UI Issues v10 — User Stories Site: Debugging & Fixing Guide

## How to reproduce / inspect issues

```bash
cd hledger-preprocessor

# Build artifacts + site and serve it:
./build_userstories.sh --serve          # http://localhost:8059/

# Or just regenerate the site (skip artifact rebuild):
./build_userstories.sh --site --serve
```

Navigate to the story page (e.g. `http://localhost:8059/stories/US-2b.1.html`)
and check for broken videos, layout issues, missing images, etc.

## Architecture overview

### Data flow: YAML → site generation → static HTML + assets

```
userstory_dag_data.yaml          Story definitions (id, title, paths, gif_video, …)
        │
        ▼
generate_site.py                 Reads YAML, discovers videos, generates HTML
        │
        ├──▶ /tmp/site/stories/US-*.html     One HTML page per story
        ├──▶ /tmp/site/assets/videos/*.mp4   Copied from gifs/*/output/
        ├──▶ /tmp/site/assets/receipts/      Receipt images
        ├──▶ /tmp/site/assets/css/           Generated CSS
        └──▶ /tmp/site/assets/js/            Generated JS (dag-sync, zoom-pane, …)
```

### Key files

| File                                       | Purpose                                                         |
| ------------------------------------------ | --------------------------------------------------------------- |
| `user_stories/dag/userstory_dag_data.yaml` | Story metadata. `gif_video` field links a story to a video stem |
| `user_stories/dag/generate_site.py`        | Site generator — HTML, CSS, JS, asset copying                   |
| `gifs/*/generate.sh`                       | Per-demo recording script (calls `common.sh` pipeline)          |
| `gifs/scripts/common.sh`                   | Shared pipeline: record → postprocess → themed GIFs → MP4       |
| `gifs/automation/stitch_full_path.py`      | Concatenates segment MP4s into a composite "full-path" video    |
| `gifs/automation/receipt_editor.py`        | Automates receipt-labelling TUI for demo recording              |
| `gifs/automation/tui_navigator.py`         | Pexpect wrapper for TUI keyboard automation                     |
| `build_userstories.sh`                     | Top-level build script (artifacts, site, GIFs, serve)           |

### How videos reach the site

1. Each `gifs/*/output/` directory contains themed MP4s (e.g. `2b_label_receipt_dracula.mp4`)
   and optionally stitched full-path videos (e.g. `2b1_full_path.mp4`)
1. `generate_site.py` calls `discover_all_videos()` which scans all `gifs/*/output/` dirs
   and builds a map: `{dir_name: {video_stem: Path}}`
1. Per story, the `gif_video` field in YAML (e.g. `gif_video: 2b1_full_path`) is looked up
   in the video map — first in the section's GIF dir, then all dirs
1. Matched videos are copied to `/tmp/site/assets/videos/`
1. Sidecar `*_markers.json` files provide node timestamps for video↔DAG sync

### How GIFs/MP4s are generated

```
generate.sh
    └─▶ common.sh:run_full_pipeline(python_module, title, rows, cols)
            1. record_demo()           asciinema recording → .cast
            2. postprocess_cast()      clean escape sequences
            3. generate_themed_gifs()  agg → themed .gif variants
            4. convert_all_gifs_to_mp4()  ffmpeg → .mp4 per theme
            5. (optional) stitch_full_path.py  concat segments → composite
```

### Stitched "full-path" videos

Some stories (like US-2b.1) stitch multiple segment videos into one composite.
For US-2b.1, `gifs/2b_label_receipt/generate.sh` stitches:

- `gifs/1a_setup_config/output/cfg_1b1w.mp4` (config setup)
- `gifs/1b_add_category/output/cat_basic.mp4` (category setup)
- `gifs/2b_label_receipt/output/2b_label_receipt_dracula.mp4` (receipt labelling)

→ Output: `gifs/2b_label_receipt/output/2b1_full_path.mp4`

The stitch script (`gifs/automation/stitch_full_path.py`) normalises fps to 25,
scales all segments to the largest resolution, and merges marker JSON sidecars.

## Debugging checklist

When a video doesn't load on a story page:

1. **Check the YAML**: does the story have `gif_video: <stem>`?

   ```bash
   grep -A5 'US-2b.1' user_stories/dag/userstory_dag_data.yaml | grep gif_video
   ```

1. **Check the source video exists and is valid**:

   ```bash
   ls -lah gifs/2b_label_receipt/output/2b1_full_path.mp4
   ffmpeg -i gifs/2b_label_receipt/output/2b1_full_path.mp4 2>&1 | grep -E 'Duration|Stream|error'
   ```

   A valid MP4 should be a few MB (not GB), have a Duration, and no "moov atom not found" errors.

1. **Check the site copy**:

   ```bash
   ls -lah /tmp/site/assets/videos/2b1_full_path.mp4
   ```

1. **Check the HTML references the right file**:

   ```bash
   grep 'video\|mp4\|gif' /tmp/site/stories/US-2b.1.html | head -5
   ```

1. **Regenerate if needed**:

   ```bash
   # Re-record a single GIF demo:
   ./build_userstories.sh --gif 2b_label_receipt --config /path/to/config.yaml

   # Just re-stitch (no re-record):
   python -m gifs.automation.stitch_full_path \
       --segments gifs/1a_setup_config/output/cfg_1b1w.mp4 \
                  gifs/1b_add_category/output/cat_basic.mp4 \
                  gifs/2b_label_receipt/output/2b_label_receipt_dracula.mp4 \
       --output gifs/2b_label_receipt/output/2b1_full_path.mp4

   # Rebuild site only (fast):
   ./build_userstories.sh --site --serve
   ```

## Common pitfalls

- **Corrupt/huge MP4 from stitch**: If input segments have different fps, the
  concat filter produces a corrupt multi-GB file. Fixed by adding `fps=25`
  normalization in `stitch_full_path.py`. Always check output file size after stitch.
- **Snap ffmpeg sandbox**: The snap-packaged ffmpeg cannot write to arbitrary `/tmp`
  paths. The stitch script writes to `gifs/*/output/` which is within the project
  tree and works fine.
- **Port already in use**: `build_userstories.sh --serve` now auto-kills any
  existing process on the target port before starting the server.

______________________________________________________________________

## Issues to fix

(Append new issues below this line)

In Full path in the DAG Diagram for us-2b.1:
Z. The boxes in the DAG should be less high, squeeze them thinner so that the DAG is less long.
A. It still contains the

Matching Parameters
box default (+-2d, exact)

box, even though the matching is done after the labelling, and it is not the matching parameters that are relevant for that, it should just show the matching algorithm flow chart at the position of the

Matching Outcome
AUTO-LINK
1 match found

box. The Matching Parameters box should be removed. The Matching Outcome box should be replaced with the matching algorithm diagram/flow.

B. The starting journal is not included for this userstory. It is also not shown in the gif. It should be shown and clickable.
C. The bank CSV transactions is not clickable, and the gif is not shown. It should be clickable and shown.
D. The Journal output is not shown and not clickable. It should.

## Constraints

Don't fake any data, don't use any synthetic videos. Ensure you regenerate the gifs from the src and test functionalities. Ensure that if the yaml is updated the tests should be updated as well. If the tests and data pieces (from the yaml) for the journal output, starting journal and bankscv do not yet exist or work properly, ensure they do. REgenerate the gifs from the test so that you know everything works reproducably toghether. (If needed you can disable generating different variants of a gif like monokai or dracula and just use 1), but you have all time in the world, just be efficient with your token consumption.
