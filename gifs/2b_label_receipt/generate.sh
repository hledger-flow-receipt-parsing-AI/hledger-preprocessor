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
python3 -u -c "
import json, re, sys, traceback
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
#    agg's idle compression + zero-gap frame inflation make it
#    impossible to predict the GIF timeline from .cast timestamps
#    alone.  Instead, we read the GIF's frame durations and build a
#    piecewise-linear mapping from raw .cast time → GIF time.
gif_path = Path('${OUTPUT_DIR}/2b_label_receipt.gif')
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

# ── 2b. Build agg-style compressed timeline ──────────────────────────
# agg compresses ALL inter-event gaps > idle_time_limit down to
# idle_time_limit.  We replicate this to get accurate GIF timestamps.
cap = idle_limit if idle_limit else 2.0
compressed_times = [0.0]
for i in range(1, len(raw_events)):
    dt = raw_events[i][0] - raw_events[i - 1][0]
    compressed_times.append(compressed_times[-1] + min(dt, cap))
compressed_duration = compressed_times[-1] if compressed_times else 0.0

# Scale compressed timeline to match actual GIF duration
gif_scale = (gif_duration / compressed_duration) if compressed_duration else 1.0

def raw_to_gif(raw_ts):
    # Binary search for the two bracketing events
    lo, hi = 0, len(raw_events) - 1
    while lo < hi - 1:
        mid = (lo + hi) // 2
        if raw_events[mid][0] <= raw_ts:
            lo = mid
        else:
            hi = mid
    if hi <= lo or raw_events[hi][0] == raw_events[lo][0]:
        return compressed_times[lo] * gif_scale
    frac = (raw_ts - raw_events[lo][0]) / (raw_events[hi][0] - raw_events[lo][0])
    ct = compressed_times[lo] + frac * (compressed_times[hi] - compressed_times[lo])
    return ct * gif_scale

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
#    Markers are set to when the field becomes VISIBLE/ACTIVE on screen,
#    NOT when the user starts typing.  This means:
#    - date: when the TUI first renders (showing 'Receipt date and time:')
#    - time: when the time digits (e.g. '10:30') first appear on screen
#    - category, bank_account, etc.: when the previous field's Enter key
#      is pressed (which triggers the TUI to activate the next field)
#    This eliminates the 0.1–1.4s lag between field becoming active and
#    the first keystroke that the old approach suffered from.
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

    # Find when TUI first renders — first event containing 'Receipt date'
    # after the initial Enter confirmation (t > 10)
    tui_render_ts = None
    for raw_t, data in events:
        if raw_t > 10 and 'Receipt date' in data:
            tui_render_ts = raw_t
            break

    result = {}

    # date + time: highlighted together since the TUI has one combined
    # 'Receipt date and time:' field typed as a single string.
    if tui_render_ts is None:
        return result
    result[f'{prefix}'] = raw_to_gif_fn(tui_render_ts - 0.5)
    result[f'{prefix}__date'] = raw_to_gif_fn(tui_render_ts)
    result[f'{prefix}__time'] = raw_to_gif_fn(tui_render_ts)

    # From here, each field activates when the PREVIOUS field's Enter
    # is pressed. The Enter triggers a TUI redraw that shows the next
    # field as active. We use the Enter timestamp as the marker.

    # date Enter → category becomes active
    date_start = first_key_after('2', 10.0)
    date_enter = first_enter_after((date_start or tui_render_ts) + 1.0)
    if date_enter:
        result[f'{prefix}__category'] = raw_to_gif_fn(date_enter)

    # category Enter → bank_account becomes active
    cat_start = first_key_after('g', date_enter or tui_render_ts + 2)
    cat_enter = first_enter_after(cat_start) if cat_start else None
    if cat_enter:
        result[f'{prefix}__bank_account'] = raw_to_gif_fn(cat_enter)

    # bank_account Enter → currency becomes active
    acct_start = first_key_after('0', cat_enter) if cat_enter else None
    acct_enter = first_enter_after(acct_start) if acct_start else None
    if acct_enter:
        result[f'{prefix}__currency'] = raw_to_gif_fn(acct_enter)

    # currency Enter → amount becomes active
    curr_start = first_key_after('9', acct_enter) if acct_enter else None
    curr_enter = first_enter_after(curr_start) if curr_start else None
    if curr_enter:
        result[f'{prefix}__amount'] = raw_to_gif_fn(curr_enter)

    # amount Enter → change becomes active
    amt_start = first_key_after('4', curr_enter) if curr_enter else None
    amt_enter = first_enter_after((amt_start or 0) + 0.5) if amt_start else None
    if amt_enter:
        result[f'{prefix}__change'] = raw_to_gif_fn(amt_enter)

    # change Enter → 'Add another account? n' (Enter) → shop address flow
    change_start = first_key_after('0', amt_enter) if amt_enter else None
    change_enter = first_enter_after(change_start) if change_start else None
    # After change Enter the 'Add another account?' widget appears.
    # 'n' is the first (pre-focused) option, so the next Enter confirms it.
    # Then the shop address selection appears.
    if change_enter:
        add_acct_enter = first_enter_after(change_enter + 0.3) if change_enter else None
        # After 'Add another account = n', shop address selection appears.
        # The next keystroke selects 'new address' (0) + Enter, then shop_name.
        if add_acct_enter:
            shop_select = first_key_after('0', add_acct_enter)
            shop_select_enter = first_enter_after(shop_select) if shop_select else None
            if shop_select_enter:
                result[f'{prefix}__shop_name'] = raw_to_gif_fn(shop_select_enter)
                prev_enter = shop_select_enter
            else:
                prev_enter = add_acct_enter
        else:
            prev_enter = change_enter
    else:
        prev_enter = None

    # Remaining shop fields: each field activates when the previous
    # field's Enter is pressed.  prev_enter is shop_select_enter (when
    # shop_name became active — already recorded above).  We skip through
    # shop_name's typing to find the Enter that transitions to shop_street,
    # then repeat for each subsequent field.
    if prev_enter:
        prev_ts = prev_enter  # shop_select_enter = when shop_name activated
        for field in ['shop_street', 'shop_house_nr', 'shop_zipcode',
                      'shop_city', 'shop_country']:
            # Find typing in the current field and its confirming Enter
            typed_ts = first_typed_after(prev_ts)
            if typed_ts is None:
                break
            enter_ts = first_enter_after(typed_ts)
            if enter_ts is None:
                break
            # This Enter confirms the PREVIOUS field and activates THIS field
            result[f'{prefix}__{field}'] = raw_to_gif_fn(enter_ts)
            prev_ts = enter_ts

        # prev_ts is now the country Enter.
        # After country: subtotal field (Enter to skip) → tax becomes active
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
    print(f'  WARNING: TUI field marker extraction failed: {e}', file=sys.stderr)
    traceback.print_exc(file=sys.stderr)

# ── 5. Write combined sidecar JSON ──────────────────────────────────
out = Path('${OUTPUT_DIR}/2b_label_receipt_markers.json')
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
RECEIPT_VIDEO="${OUTPUT_DIR}/2b_label_receipt.mp4"
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
