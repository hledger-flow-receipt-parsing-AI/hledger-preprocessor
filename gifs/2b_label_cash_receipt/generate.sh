#!/usr/bin/env bash
# =============================================================================
# Label Cash Receipt Demo - GIF Generator
#
# 1. Records the segment-only cash receipt editing TUI demo.
# 2. Stitches cfg_1b1w + cat_basic + starting_journal + receipt segment +
#    journal_output into a full-path video for US-2b.2
#    (config → categories → journal → receipt labelling → output).
# =============================================================================

set -euo pipefail

# Source common utilities
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/../scripts/common.sh"

# Initialize demo (sets up paths, runs preflight checks)
init_demo "2b_label_cash_receipt" "$@"

# ── Step 1: Record the segment-only cash receipt editing demo ─────────
run_full_pipeline \
    "gifs.automation.real_label_cash_receipt_demo" \
    "Step 2b: Label Your Cash Receipt" \
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
gif_path = Path('${OUTPUT_DIR}/2b_label_cash_receipt.gif')
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

# Find the single large compressed gap (> 5 s in the raw timeline).
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
    gap_raw_dt     = seg2_raw_start - seg1_raw_end
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
        print(f'  Warning: could not locate compressed gap frame, falling back to linear mapping',
              file=sys.stderr)
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
raw_markers = {}
for i, (raw_t, data) in enumerate(raw_events):
    for m in re.finditer(r'@@NODE:(\w+)@@', data):
        nid = m.group(1)
        if nid not in markers:
            markers[nid] = round(raw_to_gif(raw_t), 2)
            raw_markers[nid] = raw_t

print(f'  Extracted {len(markers)} structural markers from .cast')
print(f'  raw duration {raw_duration:.2f}s -> GIF {gif_duration:.2f}s')

# ── 4. Extract TUI field markers from .cast content events ───────────
def extract_field_markers_from_cast(events, raw_to_gif_fn):
    key_events = []
    for raw_t, data in events:
        if '49;' not in data:
            continue
        m = re.search(r'\[\s*(\S+?)\s*\]', data)
        if m:
            key_events.append((raw_t, m.group(1)))

    if not key_events:
        return {}

    prefix = 'tui_coffee_cash'

    def first_key_after(char, after):
        for t, k in key_events:
            if t > after and k == char:
                return t
        return None

    def first_enter_after(after):
        for t, k in key_events:
            if t > after and k == 'Enter':
                return t
        return None

    def first_typed_after(after):
        for t, k in key_events:
            if t > after and k not in ('Enter', 'Right'):
                return t
        return None

    tui_render_ts = None
    for raw_t, data in events:
        if raw_t > 10 and 'Receipt date' in data:
            tui_render_ts = raw_t
            break

    result = {}

    if tui_render_ts is None:
        return result
    result[f'{prefix}'] = raw_to_gif_fn(tui_render_ts - 0.5)
    result[f'{prefix}__date'] = raw_to_gif_fn(tui_render_ts)
    result[f'{prefix}__time'] = raw_to_gif_fn(tui_render_ts)

    date_start = first_key_after('2', 10.0)
    date_enter = first_enter_after((date_start or tui_render_ts) + 1.0)
    if date_enter:
        result[f'{prefix}__category'] = raw_to_gif_fn(date_enter)

    cat_start = first_key_after('f', date_enter or tui_render_ts + 2)
    cat_enter = first_enter_after(cat_start) if cat_start else None
    if cat_enter:
        result[f'{prefix}__bank_account'] = raw_to_gif_fn(cat_enter)

    acct_start = first_key_after('1', cat_enter) if cat_enter else None
    acct_enter = first_enter_after(acct_start) if acct_start else None
    if acct_enter:
        result[f'{prefix}__currency'] = raw_to_gif_fn(acct_enter)

    curr_start = first_key_after('9', acct_enter) if acct_enter else None
    curr_enter = first_enter_after(curr_start) if curr_start else None
    if curr_enter:
        result[f'{prefix}__amount'] = raw_to_gif_fn(curr_enter)

    amt_start = first_key_after('2', curr_enter) if curr_enter else None
    amt_enter = first_enter_after((amt_start or 0) + 0.5) if amt_start else None
    if amt_enter:
        result[f'{prefix}__change'] = raw_to_gif_fn(amt_enter)

    change_start = first_key_after('1', amt_enter) if amt_enter else None
    change_enter = first_enter_after(change_start) if change_start else None
    if change_enter:
        right_key = first_key_after('Right', change_enter)
        done_enter = first_enter_after(right_key) if right_key else None
        if done_enter:
            shop_select = first_key_after('0', done_enter)
            shop_select_enter = first_enter_after(shop_select) if shop_select else None
            if shop_select_enter:
                result[f'{prefix}__shop_name'] = raw_to_gif_fn(shop_select_enter)
                prev_enter = shop_select_enter
            else:
                prev_enter = done_enter
        else:
            prev_enter = change_enter
    else:
        prev_enter = None

    if prev_enter:
        prev_ts = prev_enter
        for field in ['shop_street', 'shop_house_nr', 'shop_zipcode',
                      'shop_city', 'shop_country']:
            typed_ts = first_typed_after(prev_ts)
            if typed_ts is None:
                break
            enter_ts = first_enter_after(typed_ts)
            if enter_ts is None:
                break
            result[f'{prefix}__{field}'] = raw_to_gif_fn(enter_ts)
            prev_ts = enter_ts

        subtotal_enter = first_enter_after(prev_ts) if prev_ts else None
        if subtotal_enter:
            result[f'{prefix}__tax'] = raw_to_gif_fn(subtotal_enter)

    return result

try:
    field_markers = extract_field_markers_from_cast(raw_events, raw_to_gif)
    for nid, gif_ts in field_markers.items():
        if nid not in markers:
            markers[nid] = round(gif_ts, 2)
    print(f'  Extracted {len(field_markers)} TUI field markers from .cast content')
except Exception as e:
    import traceback
    print(f'  WARNING: TUI field marker extraction failed: {e}', file=sys.stderr)
    traceback.print_exc(file=sys.stderr)

# ── 5. Write combined sidecar JSON ──────────────────────────────────
out = Path('${OUTPUT_DIR}/2b_label_cash_receipt_markers.json')
out.write_text(json.dumps({'markers': markers, 'total_duration': total_duration}, indent=2) + '\n')
print(f'  Total: {len(markers)} markers -> {out}')
"

# ── Step 2: Stitch full-path video for US-2b.2 ───────────────────────
if [[ "${SKIP_STITCH:-0}" == "1" ]]; then
    log "Skipping stitch step (SKIP_STITCH=1)"
else
GIFS_ROOT="${SCRIPT_DIR}/.."
CFG_VIDEO="${GIFS_ROOT}/1a_setup_config/output/cfg_1b1w.mp4"
CAT_VIDEO="${GIFS_ROOT}/1b_add_category/output/cat_basic.mp4"
STARTJ_VIDEO="${GIFS_ROOT}/2b_data_files/output/starting_journal.mp4"
RECEIPT_VIDEO="${OUTPUT_DIR}/2b_label_cash_receipt.mp4"
JRNL_VIDEO="${GIFS_ROOT}/2b_data_files/output/journal_output.mp4"
FULL_PATH_VIDEO="${OUTPUT_DIR}/2b2_full_path.mp4"

ALL_SEGMENTS=("$CFG_VIDEO" "$CAT_VIDEO" "$STARTJ_VIDEO" "$RECEIPT_VIDEO" "$JRNL_VIDEO")
MISSING=()
for seg in "${ALL_SEGMENTS[@]}"; do
    [[ -f "$seg" ]] || MISSING+=("$seg")
done

if [[ ${#MISSING[@]} -eq 0 ]]; then
    log "Stitching full-path video: cfg_1b1w + cat_basic + starting_journal + cash_receipt + journal_output"
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
