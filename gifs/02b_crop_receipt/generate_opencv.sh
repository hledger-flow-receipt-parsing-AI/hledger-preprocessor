#!/usr/bin/env bash
# =============================================================================
# Receipt Rotation & Cropping Demo (OpenCV) - GIF Generator
#
# Generates GIFs showing the actual receipt processing workflow:
# 1. Rotation TUI - rotating a sideways receipt image
# 2. Cropping TUI - selecting the receipt area with crop rectangle
#
# Unlike the ASCII simulation in generate.sh, this shows the ACTUAL visual
# interface that users will see when processing receipt images, with real
# OpenCV overlays and terminal output side-by-side.
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

header "Receipt Rotation & Cropping Demo Generator"

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
log "Generating complete workflow demo (rotation + cropping)..."
cd "$PROJECT_ROOT"
python -m gifs.automation.opencv_rotate_crop_demo

# Optimize the GIFs
WORKFLOW_GIF="${OUTPUT_DIR}/02b_crop_receipt_workflow.gif"
OPENCV_ONLY_GIF="${OUTPUT_DIR}/02b_crop_receipt_opencv_only.gif"

if command -v gifsicle >/dev/null 2>&1; then
    log "Optimizing GIFs with gifsicle..."
    for gif in "$WORKFLOW_GIF" "$OPENCV_ONLY_GIF"; do
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
echo "     Terminal + OpenCV side-by-side ($(du -h "$WORKFLOW_GIF" | cut -f1))"
echo
echo "  2. ${OPENCV_ONLY_GIF}"
echo "     OpenCV frames only ($(du -h "$OPENCV_ONLY_GIF" | cut -f1))"
echo
echo "Add to README.md:"
echo "  ![Rotation & Cropping Workflow](gifs/02b_crop_receipt/output/02b_crop_receipt_workflow.gif)"
echo
