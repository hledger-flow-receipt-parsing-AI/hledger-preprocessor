#!/usr/bin/env bash
# =============================================================================
# hledger-preprocessor Demo Recorder → GIF Generator
# Creates a clean asciinema recording and converts it to an optimized GIF
# with beautiful color-coded feedback
# =============================================================================

set -euo pipefail

# ------------------------- Configuration Variables ---------------------------
CONFIG_FILEPATH="${1:?Error: Missing config file path argument.}"
export CONFIG_FILEPATH

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

OUTPUT_CAST="${SCRIPT_DIR}/demo.cast"
OUTPUT_GIF="${SCRIPT_DIR}/demo.gif"

# ----------------------------- Colors ---------------------------------------
RED="$(tput setaf 1)"
GREEN="$(tput setaf 2)"
PURPLE="$(tput setaf 5)"
ORANGE="$(tput setaf 3)"
BOLD="$(tput bold)"
RESET="$(tput sgr0)"

# ------------------------- Recording Settings --------------------------------
RECORDER_TITLE="hledger-preprocessor receipt matcher"
ROWS=50
COLS=120
IDLE_TIME_LIMIT=2
FONT_SIZE=18
THEME="solarized-dark"

# ----------------------------- Functions ------------------------------------
log()    { echo -e "${BOLD}${GREEN}[+]${RESET} $*" ; }
warn()   { echo -e "${BOLD}${ORANGE}[!]${RESET} $*" ; }
error()  { echo -e "${BOLD}${RED}[✗]${RESET} $*" ; }
header() { echo -e "${PURPLE}${BOLD}=== $1 ===${RESET}" ; }

# ----------------------------- Pre-flight Checks ----------------------------
header "hledger-preprocessor Demo Recorder"

# Check we're in the right conda environment
if [[ "$(python -c 'import sys; print(sys.executable)' 2>/dev/null || echo '')" != */hledger_preprocessor/* ]]; then
    error "Not in the 'hledger_preprocessor' conda environment!"
    warn "Please run: conda activate hledger_preprocessor"
    exit 1
fi

log "Using config: ${CONFIG_FILEPATH}"

# Remove old files
rm -f "$OUTPUT_CAST" "$OUTPUT_GIF"

# ----------------------------- Recording ------------------------------------
header "Starting asciinema recording..."

# Run the Python automation module via asciinema
if asciinema rec "$OUTPUT_CAST" \
    --command="python -m gifs.automation.receipt_editor" \
    --title "$RECORDER_TITLE" \
    --idle-time-limit="$IDLE_TIME_LIMIT" \
    --rows "$ROWS" \
    --cols "$COLS" \
    --env="CONFIG_FILEPATH,PYTHONPATH" \
    -y -q; then
    log "Recording completed successfully → ${OUTPUT_CAST}"
else
    error "asciinema recording failed!"
    exit 1
fi

# ----------------------------- Post-process cast file ------------------------
log "Post-processing cast file..."
CAST_FILE="$OUTPUT_CAST" python -m gifs.automation.cast_postprocess

# ----------------------------- GIF Conversion -------------------------------
header "Converting to GIF using agg..."

# Ensure agg is available
if ! python -c "import agg" &>/dev/null; then
    log "Installing agg (asciinema → GIF converter)..."
    pip install -q agg || { error "Failed to install agg"; exit 1; }
fi

echo
if asciinema-agg "$OUTPUT_CAST" "$OUTPUT_GIF" \
    --theme "$THEME" \
    --font-size "$FONT_SIZE"; then
    log "GIF created successfully: ${BOLD}${OUTPUT_GIF}${RESET}"
    echo
    echo "   Just add this to your README.md:"
    echo
    echo "   ![hledger-preprocessor demo](${OUTPUT_GIF})"
    echo
else
    error "GIF conversion failed (asciinema-agg error)"
    exit 1
fi

# Optional: Optimize with gifsicle if available
if command -v gifsicle >/dev/null 2>&1; then
    log "Optimizing GIF with gifsicle..."
    gifsicle -O3 --lossy=80 -o "${OUTPUT_GIF}.tmp" "$OUTPUT_GIF" && mv "${OUTPUT_GIF}.tmp" "$OUTPUT_GIF"
    log "Optimized! Size: $(du -h "$OUTPUT_GIF" | cut -f1)"
fi

exit 0
