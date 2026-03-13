#!/usr/bin/env bash
# =============================================================================
# Split-Payment Receipt Labelling Demo - GIF Generator
#
# 1. Records the segment-only split-payment receipt TUI demo.
# 2. Stitches cfg_1b1w + cat_extended + receipt segment into a full-path
#    video for US-2b.4 (config → categories → receipt labelling).
# =============================================================================

set -euo pipefail

# Source common utilities
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/../scripts/common.sh"

# Initialize demo (sets up paths, runs preflight checks)
init_demo "2b_label_split_payment" "$@"

# ── Step 1: Record the segment-only split-payment receipt demo ────────
run_full_pipeline \
    "gifs.automation.real_label_split_payment_tui_demo" \
    "Step 2b: Label Split-Payment Receipt (Card + Cash)" \
    50 \
    120

# ── Step 1b: Build sidecar JSON from .cast markers ───────────────────
log "Building markers sidecar JSON..."
python3 -u -c "
import json, re, sys
sys.stdout.reconfigure(line_buffering=True)
from pathlib import Path
from PIL import Image

# ── 1. Parse .cast events ───────────────────────────────────────────
cast_path = Path('${CAST_FILE}')
with open(cast_path) as f:
    header = json.loads(f.readline())
    idle_limit = header.get('idle_time_limit')
    raw_events = []
    for line in f:
        row = json.loads(line)
        raw_events.append((row[0], row[2]))

raw_duration = raw_events[-1][0] if raw_events else 0.0

# ── 2. Read the actual GIF frame timing (ground truth) ──────────────
gif_path = Path('${OUTPUT_DIR}/2b_label_split_payment.gif')
img = Image.open(gif_path)
gif_durs_ms = []
try:
    while True:
        gif_durs_ms.append(img.info.get('duration', 100))
        img.seek(img.tell() + 1)
except EOFError:
    pass
gif_cum = [0.0]
for d in gif_durs_ms:
    gif_cum.append(gif_cum[-1] + d / 1000.0)
gif_duration = gif_cum[-1]

AGG_THRESHOLD = 5.0
gap_event = None
for i in range(1, len(raw_events)):
    if raw_events[i][0] - raw_events[i - 1][0] > AGG_THRESHOLD:
        gap_event = i
        break

if gap_event is not None:
    seg1_raw_start = raw_events[0][0]
    seg1_raw_end   = raw_events[gap_event - 1][0]
    seg2_raw_start = raw_events[gap_event][0]
    seg2_raw_end   = raw_events[-1][0]
    compressed_dt  = idle_limit if idle_limit else 2.0
    target_ms = int(compressed_dt * 1000)
    candidates = [fi for fi, d in enumerate(gif_durs_ms) if d == target_ms]
    gap_frame = None
    if len(candidates) == 1:
        gap_frame = candidates[0]
    elif candidates:
        expected_frac = gap_event / len(raw_events)
        best_fi = None
        best_err = float('inf')
        for fi in candidates:
            frac = fi / len(gif_durs_ms)
            err = abs(frac - expected_frac)
            if err < best_err:
                best_err = err
                best_fi = fi
        gap_frame = best_fi
    if gap_frame is None:
        seg2_raw_start = seg2_raw_end = None
        seg1_raw_end = raw_events[-1][0]
        seg1_gif_start = gif_cum[0]
        seg1_gif_end = gif_cum[-1]
    else:
        seg1_gif_start = gif_cum[0]
        seg1_gif_end   = gif_cum[gap_frame]
        seg2_gif_start = gif_cum[gap_frame + 1]
        seg2_gif_end   = gif_cum[-1]
else:
    seg1_raw_start = raw_events[0][0]
    seg1_raw_end   = raw_events[-1][0]
    seg1_gif_start = gif_cum[0]
    seg1_gif_end   = gif_cum[-1]
    seg2_raw_start = seg2_raw_end = None

seg1_span = seg1_raw_end - seg1_raw_start
seg1_scale = ((seg1_gif_end - seg1_gif_start) / seg1_span) if seg1_span else 1.0
if seg2_raw_start is not None:
    seg2_span = seg2_raw_end - seg2_raw_start
    seg2_scale = ((seg2_gif_end - seg2_gif_start) / seg2_span) if seg2_span else 1.0

def raw_to_gif(raw_ts):
    if seg2_raw_start is None or raw_ts <= seg1_raw_end:
        return seg1_gif_start + (raw_ts - seg1_raw_start) * seg1_scale
    elif raw_ts >= seg2_raw_start:
        return seg2_gif_start + (raw_ts - seg2_raw_start) * seg2_scale
    else:
        frac = (raw_ts - seg1_raw_end) / (seg2_raw_start - seg1_raw_end)
        return seg1_gif_end + frac * (seg2_gif_start - seg1_gif_end)

total_duration = round(gif_duration, 2)

# ── 3. Extract structural markers from .cast ────────────────────────
markers = {}
for i, (raw_t, data) in enumerate(raw_events):
    for m in re.finditer(r'@@NODE:(\w+)@@', data):
        nid = m.group(1)
        if nid not in markers:
            markers[nid] = round(raw_to_gif(raw_t), 2)

print(f'  Extracted {len(markers)} structural markers from .cast')
print(f'  raw duration {raw_duration:.2f}s -> GIF {gif_duration:.2f}s')

# ── 4. Write combined sidecar JSON ──────────────────────────────────
out = Path('${OUTPUT_DIR}/2b_label_split_payment_markers.json')
out.write_text(json.dumps({'markers': markers, 'total_duration': total_duration}, indent=2) + '\n')
print(f'  Total: {len(markers)} markers -> {out}')
"

# ── Step 2: Stitch full-path video for US-2b.4 ───────────────────────
if [[ "${SKIP_STITCH:-0}" == "1" ]]; then
    log "Skipping stitch step (SKIP_STITCH=1)"
else
GIFS_ROOT="${SCRIPT_DIR}/.."
CFG_VIDEO="${GIFS_ROOT}/1a_setup_config/output/cfg_1b1w.mp4"
CAT_VIDEO="${GIFS_ROOT}/1b_add_category/output/cat_basic.mp4"
RECEIPT_VIDEO="${OUTPUT_DIR}/2b_label_split_payment.mp4"
FULL_PATH_VIDEO="${OUTPUT_DIR}/2b4_full_path.mp4"

ALL_SEGMENTS=("$CFG_VIDEO" "$CAT_VIDEO" "$RECEIPT_VIDEO")
MISSING=()
for seg in "${ALL_SEGMENTS[@]}"; do
    [[ -f "$seg" ]] || MISSING+=("$seg")
done

if [[ ${#MISSING[@]} -eq 0 ]]; then
    log "Stitching full-path video: cfg_1b1w + cat_basic + split_payment_receipt"
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
