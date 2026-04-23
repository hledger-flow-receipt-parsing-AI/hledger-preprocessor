#!/usr/bin/env bash
# =============================================================================
# Label Receipt Mismatch Demo - GIF Generator
#
# Demonstrates US-2b.10: Receipt Jan 15, CSV Jan 18 (3-day delay).
# Default +/-2 day window misses → inline matching CLI widens → match found.
#
# This is a standalone demo that creates its own test environment
# (does not depend on setup_test_environment.py).
#
# 1. Records the segment-only mismatch + inline matching CLI demo.
# 2. Stitches cfg_1b1w + cat_basic + starting_journal +
#    bank_csv_ekoplaza_delayed + mismatch_receipt + journal_output
#    into a full-path video for US-2b.10.
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
OUTPUT_DIR="${SCRIPT_DIR}/output"
RECORDINGS_DIR="${SCRIPT_DIR}/recordings"
DEMO_NAME="2b_label_receipt_mismatch"

# Colors for output
GREEN="\033[0;32m"
YELLOW="\033[0;33m"
CYAN="\033[0;36m"
RED="\033[0;31m"
RESET="\033[0m"

log() { echo -e "${GREEN}[+]${RESET} $*"; }
warn() { echo -e "${YELLOW}[!]${RESET} $*"; }
error() { echo -e "${RED}[✗]${RESET} $*"; }
header() { echo -e "${CYAN}=== $1 ===${RESET}"; }

header "Label Receipt Mismatch Demo (US-2b.10)"

# Ensure directories exist
mkdir -p "$OUTPUT_DIR" "$RECORDINGS_DIR"

# Use PYTHON env var if set, otherwise use python from PATH
PYTHON="${PYTHON:-python}"

# Check conda environment
if ! "$PYTHON" -c "import hledger_preprocessor" 2>/dev/null; then
    error "hledger_preprocessor not importable. Activate conda environment first."
    warn "Run: conda activate hledger_preprocessor"
    exit 1
fi

# Check for asciinema
if ! command -v asciinema >/dev/null 2>&1; then
    error "asciinema not found!"
    warn "Install with: pip install asciinema"
    exit 1
fi

# Check for agg (asciinema to GIF converter)
if ! command -v asciinema-agg >/dev/null 2>&1; then
    if ! command -v agg >/dev/null 2>&1; then
        error "asciinema-agg not found!"
        warn "Install with: pip install agg"
        exit 1
    fi
fi

# Determine agg command
AGG_CMD="asciinema-agg"
command -v asciinema-agg >/dev/null 2>&1 || AGG_CMD="agg"

# ── Step 1: Record the demo ─────────────────────────────────────────────
CAST_FILE="${RECORDINGS_DIR}/${DEMO_NAME}.cast"
log "Recording mismatch demo with asciinema..."
rm -f "$CAST_FILE"

cd "$PROJECT_ROOT"
export PYTHONPATH="${PROJECT_ROOT}:${PYTHONPATH:-}"

asciinema rec "$CAST_FILE" \
    --command="$PYTHON -m gifs.automation.real_label_receipt_mismatch_demo" \
    --title "Step 2b.10: Inline Matching CLI (Mismatch)" \
    --idle-time-limit=2 \
    --rows 50 \
    --cols 120 \
    -y -q

log "Recording completed → ${CAST_FILE}"

# Post-process the cast file (clean up escape sequences)
log "Post-processing cast file..."
CAST_FILE="$CAST_FILE" "$PYTHON" -m gifs.automation.cast_postprocess || true

# ── Step 1b: Generate GIF ───────────────────────────────────────────────
OUTPUT_GIF="${OUTPUT_DIR}/${DEMO_NAME}.gif"
log "Generating GIF..."

$AGG_CMD "$CAST_FILE" "$OUTPUT_GIF" \
    --theme dracula \
    --font-size 20 \
    --renderer resvg \
    --line-height 1.2

log "Generated: ${OUTPUT_GIF}"

# Optimize the GIF
if command -v gifsicle >/dev/null 2>&1; then
    log "Optimizing GIF with gifsicle..."
    gifsicle -O3 "$OUTPUT_GIF" -o "${OUTPUT_GIF}.tmp" 2>/dev/null || true
    if [[ -f "${OUTPUT_GIF}.tmp" ]]; then
        mv "${OUTPUT_GIF}.tmp" "$OUTPUT_GIF"
    fi
fi

# ── Step 1c: Convert GIF to MP4 ────────────────────────────────────────
convert_gif_to_mp4() {
    local gif_file="$1"
    local mp4_file="${gif_file%.gif}.mp4"

    if ! command -v ffmpeg >/dev/null 2>&1; then
        log "ffmpeg not found, skipping MP4 conversion"
        return 0
    fi

    log "Converting GIF to MP4..."
    if ffmpeg -y -i "$gif_file" \
        -movflags faststart \
        -pix_fmt yuv420p \
        -vf "scale=trunc(iw/2)*2:trunc(ih/2)*2" \
        -c:v libx264 \
        -crf 23 \
        -preset medium \
        "$mp4_file" 2>/dev/null; then
        log "MP4 created at: $mp4_file"
    else
        log "MP4 conversion failed (non-fatal)"
    fi
}

convert_gif_to_mp4 "$OUTPUT_GIF"

# ── Step 1d: Extract markers sidecar JSON ───────────────────────────────
log "Extracting markers from cast file..."
python3 -u -c "
import json, re
from pathlib import Path

cast_path = Path('${CAST_FILE}')
with open(cast_path) as f:
    header = json.loads(f.readline())
    idle_limit = header.get('idle_time_limit', 2.0)
    raw_events = []
    for line in f:
        row = json.loads(line)
        raw_events.append((row[0], row[2]))

if not raw_events:
    print('  No events in cast file')
    exit(0)

raw_duration = raw_events[-1][0]

# Build agg-style compressed timeline
cap = idle_limit if idle_limit else 2.0
compressed_times = [0.0]
for i in range(1, len(raw_events)):
    dt = raw_events[i][0] - raw_events[i - 1][0]
    compressed_times.append(compressed_times[-1] + min(dt, cap))
compressed_duration = compressed_times[-1] if compressed_times else 0.0

# Try to read actual GIF duration for scaling
gif_path = Path('${OUTPUT_DIR}/${DEMO_NAME}.gif')
try:
    from PIL import Image
    img = Image.open(gif_path)
    gif_durs_ms = []
    try:
        while True:
            gif_durs_ms.append(img.info.get('duration', 100))
            img.seek(img.tell() + 1)
    except EOFError:
        pass
    gif_duration = sum(gif_durs_ms) / 1000.0
except Exception:
    gif_duration = compressed_duration

gif_scale = (gif_duration / compressed_duration) if compressed_duration else 1.0

def raw_to_gif(raw_ts):
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

# Extract structural markers
markers = {}
for i, (raw_t, data) in enumerate(raw_events):
    for m in re.finditer(r'@@NODE:(\w+)@@', data):
        nid = m.group(1)
        if nid not in markers:
            markers[nid] = round(raw_to_gif(raw_t), 2)

total_duration = round(gif_duration, 2)
print(f'  Extracted {len(markers)} structural markers from .cast')
print(f'  raw duration {raw_duration:.2f}s -> GIF {gif_duration:.2f}s')

# Write sidecar JSON
out = Path('${OUTPUT_DIR}/${DEMO_NAME}_markers.json')
out.write_text(json.dumps({'markers': markers, 'total_duration': total_duration}, indent=2) + '\n')
print(f'  Total: {len(markers)} markers -> {out}')
"

# ── Step 2: Stitch full-path video for US-2b.10 ────────────────────────
if [[ "${SKIP_STITCH:-0}" == "1" ]]; then
    log "Skipping stitch step (SKIP_STITCH=1)"
else
    GIFS_ROOT="${SCRIPT_DIR}/.."
    CFG_VIDEO="${GIFS_ROOT}/1a_setup_config/output/cfg_1b1w.mp4"
    CAT_VIDEO="${GIFS_ROOT}/1b_add_category/output/cat_basic.mp4"
    STARTJ_VIDEO="${GIFS_ROOT}/2b_data_files/output/starting_journal.mp4"
    CSV_VIDEO="${GIFS_ROOT}/2b_data_files/output/bank_csv_ekoplaza_delayed.mp4"
    RECEIPT_VIDEO="${OUTPUT_DIR}/${DEMO_NAME}.mp4"
    JRNL_VIDEO="${GIFS_ROOT}/2b_data_files/output/journal_output.mp4"
    FULL_PATH_VIDEO="${OUTPUT_DIR}/2b10_full_path.mp4"

    ALL_SEGMENTS=("$CFG_VIDEO" "$CAT_VIDEO" "$STARTJ_VIDEO" "$CSV_VIDEO" "$RECEIPT_VIDEO" "$JRNL_VIDEO")
    MISSING=()
    for seg in "${ALL_SEGMENTS[@]}"; do
        [[ -f "$seg" ]] || MISSING+=("$seg")
    done

    if [[ ${#MISSING[@]} -eq 0 ]]; then
        log "Stitching full-path video: cfg_1b1w + cat_basic + starting_journal + bank_csv_delayed + receipt_mismatch + journal_output"
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
fi

# ── Summary ─────────────────────────────────────────────────────────────
echo
header "Summary"
echo
log "Generated GIF:"
echo "  ${OUTPUT_GIF}"
echo "  Size: $(du -h "$OUTPUT_GIF" 2>/dev/null | cut -f1 || echo 'N/A')"
echo
echo "Scenario: Receipt Jan 15 | CSV Jan 18 | Default margin +/-2d → miss"
echo "  → User enters matching CLI inline → widens to +/-5d → match found"
echo

exit 0
