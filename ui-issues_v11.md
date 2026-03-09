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
A. Can you highlight the receipt when  the box:

Receipt Images
ekoplaza_card.jpg

is highlighted?

B. When filling the receipt data in the tui, can you highlight the related text in the receipt image?
E.g.:
B.1 the date, show where it comes from when the date is typed.
B.2 the time, show where it comes from when the time is typed.
B.2.a the the account, show with which account the receipt was payed, (currently this information is missing from the receipt, add it like: payed with card and then have XXXX5342 to represent the last 4 numbers of the triodos csv account that was used to pay with for the receipt (even though that card number is currently not in the account name, that is fine)). 
B.2.b The userstory is about paying by card with the triodos debit card. and the 2 correct account informations are typed in the config, (EUR physical wallet and Triodos checking (EUR csv). But those accounts are not shown in the TUI receipt labelling gif. Could it be that you did not use the config that is typed in the config.gif for the receipt label gif? If so, ensure it does, and that it works.

B.3 the currency (EUR), show where it comes from when the currency is selected.
B.4 the amount paid for the receipt, show where it comes from when the the amount paid from that account is typed.
B.5 the change returned (0, it is currently not on the receipt image), show where it comes from when the change returned from that bank account is typed.

C.a Can you make it go to the ( )n button when you go to the right to answer Add another account (y/n)? Currently 
- after entering the change returned, the cursor goes to the start/C of "Change returned to account,  
- Then upon enter it goes to the middle of ( ) y brackets
- Then the cursor goes to the start of the line so to the ()
- Then simultaneously the (X) n gets fild and the cursor goes to the next question (answering position). 
C.b The cursor should go to the middle of the ( ) y brackets at the start, then it should go to the middle of the ( ) n brackets then upon pressing enter, the ( ) n should change to (x) n and the cursor should move to the next question. It already goes to the right positition of the next question currently.

B.6 the shop name (Ekoplaza), show where it comes from when the shop name is typed.
B.7 the shop street (the street is currently not shown on the receipt), show where it comes from when the street is typed.
B.7 the house nr (the house nr is currently not shown on the receipt), show where it comes from when the house nr is typed.
B.7 the zip code (the zip code is currently not shown on the receipt), show where it comes from when the zip code is typed.
B.7 the city (Amsterdam), show where it comes from when the city is typed.
B.8 the country (NL), show where it comes from when the country is typed.
B.8 the tax, show where it comes from when the tax is typed.


D. The box:
Receipt Labels (JSON
ekoplaza_card
EUR 42.17 card 

Should be split into the following 3 subboxes:
Receipt Labelling - show initial receipt does not exsist
Label receipt in TUI, based on image
Receipt Labelling - show Receipt label output json

E. The matching currently is fake. It should be generated by calling src code (don't change src code.) It should show a diff on how the receipt has been changed by including the reference to the csv transaction, and how the bankcsv transaction (if this is done, I currently don't know) is linked to the .csv.

Verify each solution works. At the end, verify 1 solution did not break another.


## Constraints

Don't fake any data, don't use any synthetic videos. Ensure you regenerate the gifs from the src and test functionalities. Ensure that if the yaml is updated the tests should be updated as well. If the tests and data pieces (from the yaml) for the journal output, starting journal and bankscv do not yet exist or work properly, ensure they do. REgenerate the gifs from the test so that you know everything works reproducably toghether. (If needed you can disable generating different variants of a gif like monokai or dracula and just use 1), but you have all time in the world, just be efficient with your token consumption.
