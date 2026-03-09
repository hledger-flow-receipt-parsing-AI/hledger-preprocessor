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
#    agg's idle compression + zero-gap frame inflation make it
#    impossible to predict the GIF timeline from .cast timestamps
#    alone.  Instead, we read the GIF's frame durations and build a
#    piecewise-linear mapping from raw .cast time → GIF time.
gif_path = Path('${OUTPUT_DIR}/2b_label_receipt_dracula.gif')
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
# agg 1.3.0 only compresses gaps exceeding its --idle-time-limit
# default of 5 s, capping them to the .cast header value.
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

    # The compressed gap appears as a frame with duration == compressed_dt * 1000.
    # There may be multiple frames with that duration (unrelated pauses that
    # happen to equal the idle_time_limit).  Pick the candidate whose position
    # best explains the overall segment durations.
    target_ms = int(compressed_dt * 1000)
    candidates = [fi for fi, d in enumerate(gif_durs_ms) if d == target_ms]

    gap_frame = None
    if len(candidates) == 1:
        gap_frame = candidates[0]
    elif candidates:
        # Expected pre-gap duration = raw pre-gap minus any sub-threshold
        # gaps that stay unchanged, so just use a ratio heuristic:
        # the gap frame should split the GIF at roughly the same fraction
        # as gap_event splits the events.
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
        print(f'  Warning: could not locate compressed gap frame (target={target_ms}ms, '
              f'candidates={candidates}), falling back to linear mapping',
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
    # No large gap — simple linear mapping
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

# ── 4. Extract TUI field markers from .cast key overlay events ──────
#    Instead of using wall-clock time.time() markers (which drift vs the
#    .cast clock), we detect the actual typed content in the .cast output
#    stream.  The key overlay renders pressed keys at row 49, col 106 as
#    '[  key  ]'.  We trace through the known field sequence matching the
#    first typed character for each field.
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

    prefix = 'tui_ekoplaza_card_eur'

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

    result = {}

    # date: first digit '2' (start of '202501151030')
    date_start = first_key_after('2', 10.0)
    if date_start is None:
        return result
    result[f'{prefix}'] = raw_to_gif_fn(date_start - 0.5)
    result[f'{prefix}__date'] = raw_to_gif_fn(date_start)

    # time: Enter after date digits
    date_enter = first_enter_after(date_start + 1.0)
    if date_enter:
        result[f'{prefix}__time'] = raw_to_gif_fn(date_enter)

    # category: first char 'g' (for 'groceries:ekoplaza')
    cat_start = first_key_after('g', date_enter or date_start + 2)
    if cat_start:
        result[f'{prefix}__category'] = raw_to_gif_fn(cat_start)

    # bank_account: '0' after category Enter
    cat_enter = first_enter_after(cat_start) if cat_start else None
    acct_start = first_key_after('0', cat_enter) if cat_enter else None
    if acct_start:
        result[f'{prefix}__bank_account'] = raw_to_gif_fn(acct_start)

    # currency: '9' after account Enter
    acct_enter = first_enter_after(acct_start) if acct_start else None
    curr_start = first_key_after('9', acct_enter) if acct_enter else None
    if curr_start:
        result[f'{prefix}__currency'] = raw_to_gif_fn(curr_start)

    # amount: '4' after currency Enter (for '42.17')
    curr_enter = first_enter_after(curr_start) if curr_start else None
    amt_start = first_key_after('4', curr_enter) if curr_enter else None
    if amt_start:
        result[f'{prefix}__amount'] = raw_to_gif_fn(amt_start)

    # change: '0' after amount Enter
    amt_enter = first_enter_after(amt_start + 0.5) if amt_start else None
    change_start = first_key_after('0', amt_enter) if amt_enter else None
    if change_start:
        result[f'{prefix}__change'] = raw_to_gif_fn(change_start)

    # shop_name: 'E' (for 'Ekoplaza') after several Enter presses
    shop_name_start = first_key_after('E', 30.0)
    if shop_name_start:
        result[f'{prefix}__shop_name'] = raw_to_gif_fn(shop_name_start)

    # Remaining shop fields: first typed char after each Enter
    prev_ts = shop_name_start
    for field in ['shop_street', 'shop_house_nr', 'shop_zipcode',
                  'shop_city', 'shop_country']:
        if prev_ts is None:
            break
        enter_ts = first_enter_after(prev_ts)
        if enter_ts is None:
            break
        typed_ts = first_typed_after(enter_ts)
        if typed_ts is None:
            break
        result[f'{prefix}__{field}'] = raw_to_gif_fn(typed_ts)
        prev_ts = typed_ts

    # tax: first typed char after subtotal Enter (skip) + country Enter
    country_enter = first_enter_after(prev_ts) if prev_ts else None
    subtotal_enter = first_enter_after(country_enter) if country_enter else None
    tax_start = first_typed_after(subtotal_enter) if subtotal_enter else None
    if tax_start:
        result[f'{prefix}__tax'] = raw_to_gif_fn(tax_start)

    return result

field_markers = extract_field_markers_from_cast(raw_events, raw_to_gif)
for nid, gif_ts in field_markers.items():
    if nid not in markers:
        markers[nid] = round(gif_ts, 2)
print(f'  Extracted {len(field_markers)} TUI field markers from .cast content')

# ── 5. Write combined sidecar JSON ──────────────────────────────────
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
