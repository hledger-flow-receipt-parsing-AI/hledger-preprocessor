#!/usr/bin/env bash
# =============================================================================
# Label Receipt Demo - GIF Generator
#
# 1. Records the segment-only receipt editing TUI demo.
# 2. Stitches cfg_1b1w + cat_basic + starting_journal + bank_csv +
#    receipt segment + journal_output into a full-path video for US-2b.1
#    (config → categories → journal → csv → receipt labelling → output).
# =============================================================================

set -euo pipefail

# Source common utilities
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/../scripts/common.sh"

# Initialize demo (sets up paths, runs preflight checks)
init_demo "2b_label_receipt" "$@"

# ── Step 1: Record the segment-only receipt editing demo ──────────────
run_full_pipeline \
    "gifs.automation.receipt_editor" \
    "Step 2b: Label Your Receipt" \
    50 \
    120

# ── Step 1b: Build sidecar JSON from .cast markers + TUI field markers ─
# Structural markers (img_*, nolbl_*, lbl_*) are emitted via emit_node_marker()
# OUTSIDE the TUI and captured in the .cast file.  Field-level markers
# (tui_*__date, tui_*__time, …) are recorded via time.time() inside the TUI
# (to avoid corrupting urwid's screen) and written to /tmp/tui_field_markers.json.
# Calibration: both sources record nolbl_ekoplaza_card_eur — the .cast version
# gives the asciinema-relative timestamp, the TUI version (_calibration_nolbl)
# gives the absolute wall-clock time.  The offset between them is used to
# convert all TUI field markers to .cast-relative timestamps.
log "Building markers sidecar JSON..."
python3 -c "
import json, re, sys
from pathlib import Path

# 1. Extract structural markers from .cast
cast_path = Path('${CAST_FILE}')
markers = {}
ts = 0.0
with open(cast_path) as f:
    f.readline()  # skip header
    for line in f:
        row = json.loads(line)
        ts, data = row[0], row[2]
        for m in re.finditer(r'@@NODE:(\w+)@@', data):
            nid = m.group(1)
            if nid not in markers:
                markers[nid] = round(ts, 2)

total_duration = round(ts, 2)
print(f'  Extracted {len(markers)} structural markers from .cast')

# 2. Merge TUI field markers (wall-clock based, need calibration)
tui_markers_path = Path('/tmp/tui_field_markers.json')
if tui_markers_path.exists():
    tui_markers = json.loads(tui_markers_path.read_text())

    # Calibrate: find the offset between .cast and wall-clock time bases
    # using the nolbl_ekoplaza_card_eur marker present in both
    cast_nolbl_ts = markers.get('nolbl_ekoplaza_card_eur')
    tui_nolbl_ts = tui_markers.pop('_calibration_nolbl', None)

    if cast_nolbl_ts is not None and tui_nolbl_ts is not None:
        offset = cast_nolbl_ts - tui_nolbl_ts
        merged = 0
        for nid, wall_ts in tui_markers.items():
            if nid not in markers:
                markers[nid] = round(wall_ts + offset, 2)
                merged += 1
        print(f'  Calibrated offset: {offset:+.2f}s, merged {merged} TUI field markers')
    else:
        print('  Warning: calibration marker missing, skipping TUI field markers',
              file=sys.stderr)

# 3. Write combined sidecar JSON
out = Path('${OUTPUT_DIR}/2b_label_receipt_dracula_markers.json')
out.write_text(json.dumps({'markers': markers, 'total_duration': total_duration}, indent=2) + '\n')
print(f'  Total: {len(markers)} markers -> {out}')
"

# ── Step 2: Stitch full-path video for US-2b.1 ───────────────────────
if [[ "${SKIP_STITCH:-0}" == "1" ]]; then
    log "Skipping stitch step (SKIP_STITCH=1)"
else
GIFS_ROOT="${SCRIPT_DIR}/.."
CFG_VIDEO="${GIFS_ROOT}/1a_setup_config/output/cfg_1b1w.mp4"
CAT_VIDEO="${GIFS_ROOT}/1b_add_category/output/cat_basic.mp4"
STARTJ_VIDEO="${GIFS_ROOT}/2b_data_files/output/starting_journal.mp4"
CSV_VIDEO="${GIFS_ROOT}/2b_data_files/output/bank_csv.mp4"
RECEIPT_VIDEO="${OUTPUT_DIR}/2b_label_receipt_dracula.mp4"
JRNL_VIDEO="${GIFS_ROOT}/2b_data_files/output/journal_output.mp4"
FULL_PATH_VIDEO="${OUTPUT_DIR}/2b1_full_path.mp4"

ALL_SEGMENTS=("$CFG_VIDEO" "$CAT_VIDEO" "$STARTJ_VIDEO" "$CSV_VIDEO" "$RECEIPT_VIDEO" "$JRNL_VIDEO")
MISSING=()
for seg in "${ALL_SEGMENTS[@]}"; do
    [[ -f "$seg" ]] || MISSING+=("$seg")
done

if [[ ${#MISSING[@]} -eq 0 ]]; then
    log "Stitching full-path video: cfg_1b1w + cat_basic + starting_journal + bank_csv + receipt + journal_output"
    python -m gifs.automation.stitch_full_path \
        --segments "${ALL_SEGMENTS[@]}" \
        --output "$FULL_PATH_VIDEO"
    log "Full-path video: ${FULL_PATH_VIDEO}"
else
    warn "Skipping full-path stitch (missing prerequisite videos)"
    for m in "${MISSING[@]}"; do
        warn "  Missing: $m"
    done
fi
fi  # end SKIP_STITCH guard

exit 0
