#!/usr/bin/env bash
# =============================================================================
# Match Receipt to CSV Demo - GIF Generator
#
# Demonstrates automatic linking of receipts to bank CSV transactions.
# This runs the REAL --link-receipts-to-transactions command against
# a test environment to show authentic CLI output.
#
# Based on the Ekoplaza receipt from gifs/assets/example_receipt_cropped.png:
# - Store: EKOPLAZA (Amsterdam, NL)
# - Date: 2025-01-15
# - Total: EUR 42.17
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
OUTPUT_DIR="${SCRIPT_DIR}/output"
RECORDINGS_DIR="${SCRIPT_DIR}/recordings"
DEMO_NAME="3_match_receipt_to_csv"

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

header "Match Receipt to CSV Demo Generator (using real CLI)"

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
    --command="$PYTHON -m gifs.automation.real_link_receipts_demo" \
    --title "Step 3: Match Receipt to CSV Transaction" \
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
echo "Note: This demo runs the REAL --link-receipts-to-transactions command"
echo "  against a temporary test environment with matching Ekoplaza data."
echo
echo "Add to README.md:"
echo "  ![Step 3: Match Receipt to CSV](gifs/3_match_receipt_to_csv/output/${DEMO_NAME}.gif)"
echo

exit 0
