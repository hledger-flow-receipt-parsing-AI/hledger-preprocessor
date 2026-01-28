#!/usr/bin/env bash
# =============================================================================
# Crop Receipt Demo - GIF Generator
#
# Demonstrates how to crop receipt images before labeling.
# This uses the actual OpenCV demo which calls the real drawing functions
# from src/hledger_preprocessor/.../drawing.py, so when src is updated,
# the GIF will reflect those changes.
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
OUTPUT_DIR="${SCRIPT_DIR}/output"

# Colors for output
GREEN="\033[0;32m"
YELLOW="\033[0;33m"
CYAN="\033[0;36m"
RESET="\033[0m"

log() { echo -e "${GREEN}[+]${RESET} $*"; }
warn() { echo -e "${YELLOW}[!]${RESET} $*"; }
header() { echo -e "${CYAN}=== $1 ===${RESET}"; }

header "Crop Receipt Demo Generator (using actual src code)"

# Ensure output directory exists
mkdir -p "$OUTPUT_DIR"

# Check for required dependencies
if ! python -c "import imageio" 2>/dev/null; then
    warn "imageio not found, installing..."
    pip install imageio
fi

if ! python -c "import cv2" 2>/dev/null; then
    echo "Error: OpenCV (cv2) not found. Install with: pip install opencv-python"
    exit 1
fi

# Generate the complete workflow GIF (rotation + cropping)
# This uses the actual rotate_images() and crop_images() functions from source code
log "Generating workflow demo using actual rotate_images() and crop_images()..."
cd "$PROJECT_ROOT"
python -m gifs.automation.real_rotate_crop_demo

# Optimize the GIFs
WORKFLOW_GIF="${OUTPUT_DIR}/2a_crop_receipt_workflow.gif"
IMAGE_GIF="${OUTPUT_DIR}/2a_crop_receipt_image.gif"
CLI_GIF="${OUTPUT_DIR}/2a_crop_receipt_cli.gif"

if command -v gifsicle >/dev/null 2>&1; then
    log "Optimizing GIFs with gifsicle..."
    for gif in "$WORKFLOW_GIF" "$IMAGE_GIF" "$CLI_GIF"; do
        if [[ -f "$gif" ]]; then
            gifsicle -O3 "$gif" -o "${gif}.tmp" 2>/dev/null || true
            if [[ -f "${gif}.tmp" ]]; then
                mv "${gif}.tmp" "$gif"
            fi
        fi
    done
fi

# Show results
echo
header "Summary"
echo
log "Generated GIFs:"
echo "  1. ${WORKFLOW_GIF}"
echo "     Terminal + OpenCV side-by-side ($(du -h "$WORKFLOW_GIF" 2>/dev/null | cut -f1 || echo 'N/A'))"
echo
echo "  2. ${IMAGE_GIF}"
echo "     Image frames only ($(du -h "$IMAGE_GIF" 2>/dev/null | cut -f1 || echo 'N/A'))"
echo
echo "  3. ${CLI_GIF}"
echo "     CLI output only ($(du -h "$CLI_GIF" 2>/dev/null | cut -f1 || echo 'N/A'))"
echo
echo "Note: This demo uses the actual drawing functions from:"
echo "  src/hledger_preprocessor/receipts_to_objects/edit_images/drawing.py"
echo "  Any changes to the source code will be reflected in the GIF."
echo

# Convert GIFs to MP4 for pausable GitHub README videos
convert_gif_to_mp4() {
    local gif_file="$1"
    local mp4_file="${gif_file%.gif}.mp4"

    if ! command -v ffmpeg >/dev/null 2>&1; then
        log "ffmpeg not found, skipping MP4 conversion"
        return 0
    fi

    log "Converting $(basename "$gif_file") to MP4..."
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

# Convert all generated GIFs to MP4
for gif in "$WORKFLOW_GIF" "$IMAGE_GIF" "$CLI_GIF"; do
    if [[ -f "$gif" ]]; then
        convert_gif_to_mp4 "$gif"
    fi
done

exit 0
