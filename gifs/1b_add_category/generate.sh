#!/usr/bin/env bash
# =============================================================================
# Add Category Demo - GIF Generator
#
# Generates one GIF per category node variant (cat_basic, cat_with_income).
# Each GIF types the matching category fragments with per-section timestamps.
# Uses yaml_typing_gif.py --segments to record per-section timestamps.
# =============================================================================

set -euo pipefail

# ================================ Config =====================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
OUTPUT_DIR="${SCRIPT_DIR}/output"
FRAG_DIR="${PROJECT_ROOT}/test/fixtures/config_fragments/categories"

# ================================ Colors =====================================
GREEN="$(tput setaf 2 2>/dev/null || echo '')"
BOLD="$(tput bold 2>/dev/null || echo '')"
RESET="$(tput sgr0 2>/dev/null || echo '')"

log() { echo -e "${BOLD}${GREEN}[+]${RESET} $*"; }

# ================================ Helpers ====================================

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

# ================================ Main =======================================

mkdir -p "$OUTPUT_DIR"

if [[ ! -d "$FRAG_DIR" ]]; then
    echo "Error: Category fragments directory not found: $FRAG_DIR"
    exit 1
fi

export PYTHONPATH="${PROJECT_ROOT}:${PYTHONPATH:-}"

# --- cat_basic: groceries + withdrawl ---
log "Generating cat_basic categories typing animation..."
python -m gifs.automation.yaml_typing_gif \
    --segments \
        "${FRAG_DIR}/groceries.yaml=cat_basic__groceries" \
        "${FRAG_DIR}/withdrawl.yaml=cat_basic__withdrawl" \
    --output "${OUTPUT_DIR}/cat_basic.gif" \
    --markers-output "${OUTPUT_DIR}/cat_basic_markers.json" \
    --title "categories.yaml" \
    --rows 35 \
    --cols 85
convert_gif_to_mp4 "${OUTPUT_DIR}/cat_basic.gif"

# --- cat_with_income: groceries + withdrawl + salary/freelance ---
log "Generating cat_with_income categories typing animation..."
python -m gifs.automation.yaml_typing_gif \
    --segments \
        "${FRAG_DIR}/groceries.yaml=cat_with_income__groceries" \
        "${FRAG_DIR}/withdrawl.yaml=cat_with_income__withdrawl" \
        "${FRAG_DIR}/salary.yaml=cat_with_income__salary" \
    --output "${OUTPUT_DIR}/cat_with_income.gif" \
    --markers-output "${OUTPUT_DIR}/cat_with_income_markers.json" \
    --title "categories.yaml" \
    --rows 35 \
    --cols 85
convert_gif_to_mp4 "${OUTPUT_DIR}/cat_with_income.gif"

log "All category GIFs generated!"
exit 0
