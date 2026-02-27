#!/usr/bin/env bash
# =============================================================================
# Split-Payment Receipt Labelling Demo - GIF Generator
#
# Demonstrates US-2b.4: Labelling a dinner receipt paid with two accounts
# (30 EUR by card + 20 EUR in cash = 50 EUR total).
# Shows two account_transactions in the receipt label JSON.
#
# This runs the REAL receipt labelling demo against
# a test environment to show authentic output.
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
OUTPUT_DIR="${SCRIPT_DIR}/output"
RECORDINGS_DIR="${SCRIPT_DIR}/recordings"
DEMO_NAME="2b_label_split_payment"

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

header "Split-Payment Receipt Labelling Demo Generator"

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
    log "Installing agg (asciinema → GIF converter)..."
    pip install -q agg || { error "Failed to install agg"; exit 1; }
fi

# Record the demo using asciinema
CAST_FILE="${RECORDINGS_DIR}/${DEMO_NAME}.cast"
log "Recording demo with asciinema..."
rm -f "$CAST_FILE"

cd "$PROJECT_ROOT"
export PYTHONPATH="${PROJECT_ROOT}:${PYTHONPATH:-}"

asciinema rec "$CAST_FILE" \
    --command="$PYTHON -m gifs.automation.real_label_split_payment_demo" \
    --title "Step 2b: Label Split-Payment Receipt (Card + Cash)" \
    --idle-time-limit=2 \
    --rows 38 \
    --cols 100 \
    -y -q

log "Recording completed → ${CAST_FILE}"

# Post-process the cast file (clean up escape sequences)
log "Post-processing cast file..."
CAST_FILE="$CAST_FILE" "$PYTHON" -m gifs.automation.cast_postprocess || true

# Generate themed GIFs
log "Generating GIFs..."
OUTPUT_GIF="${OUTPUT_DIR}/${DEMO_NAME}.gif"

# Default theme (dracula)
asciinema-agg "$CAST_FILE" "$OUTPUT_GIF" \
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

# Show results
echo
header "Summary"
echo
log "Generated GIF:"
echo "  ${OUTPUT_GIF}"
echo "  Size: $(du -h "$OUTPUT_GIF" 2>/dev/null | cut -f1 || echo 'N/A')"
echo
echo "Note: This demo shows labelling a 50 EUR dinner receipt with"
echo "  two payment accounts (30 EUR card + 20 EUR cash)."
echo

# Convert GIF to MP4 for pausable GitHub README videos
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

exit 0
