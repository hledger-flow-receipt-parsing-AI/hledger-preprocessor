#!/usr/bin/env bash
# =============================================================================
# Add Category Demo - GIF Generator
#
# Demonstrates how to add spending categories to categories.yaml
# Uses yaml_typing_gif.py to render actual YAML file with typing animation
# =============================================================================

set -euo pipefail

# ================================ Config =====================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
DEMO_NAME="02_add_category"
OUTPUT_DIR="${SCRIPT_DIR}/output"

# Input YAML file - use the test fixture
INPUT_YAML="${PROJECT_ROOT}/test/fixtures/categories/example_categories.yaml"
OUTPUT_GIF="${OUTPUT_DIR}/${DEMO_NAME}.gif"

# ================================ Colors =====================================
GREEN="$(tput setaf 2 2>/dev/null || echo '')"
BOLD="$(tput bold 2>/dev/null || echo '')"
RESET="$(tput sgr0 2>/dev/null || echo '')"

log() { echo -e "${BOLD}${GREEN}[+]${RESET} $*"; }

# ================================ Main =======================================

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Check input file exists
if [[ ! -f "$INPUT_YAML" ]]; then
    echo "Error: Input YAML not found: $INPUT_YAML"
    exit 1
fi

log "Generating categories.yaml typing animation..."
log "  Input: $INPUT_YAML"
log "  Output: $OUTPUT_GIF"

# Ensure PYTHONPATH includes project root
export PYTHONPATH="${PROJECT_ROOT}:${PYTHONPATH:-}"

# Generate the GIF using yaml_typing_gif.py
python -m gifs.automation.yaml_typing_gif \
    --input "$INPUT_YAML" \
    --output "$OUTPUT_GIF" \
    --title "categories.yaml" \
    --rows 35 \
    --cols 85

log "Done! GIF created at: $OUTPUT_GIF"

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
