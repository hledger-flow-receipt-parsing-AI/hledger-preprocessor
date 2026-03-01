#!/usr/bin/env bash
# =============================================================================
# Label Receipt Demo - GIF Generator
#
# 1. Records the segment-only receipt editing TUI demo.
# 2. Stitches cfg_1b1w + cat_basic + receipt segment into a full-path video
#    for US-2b.1 (config → categories → receipt labelling).
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

# ── Step 2: Stitch full-path video for US-2b.1 ───────────────────────
GIFS_ROOT="${SCRIPT_DIR}/.."
CFG_VIDEO="${GIFS_ROOT}/1a_setup_config/output/cfg_1b1w.mp4"
CAT_VIDEO="${GIFS_ROOT}/1b_add_category/output/cat_basic.mp4"
RECEIPT_VIDEO="${OUTPUT_DIR}/2b_label_receipt_dracula.mp4"
FULL_PATH_VIDEO="${OUTPUT_DIR}/2b1_full_path.mp4"

if [[ -f "$CFG_VIDEO" && -f "$CAT_VIDEO" && -f "$RECEIPT_VIDEO" ]]; then
    log "Stitching full-path video: cfg_1b1w + cat_basic + receipt segment"
    python -m gifs.automation.stitch_full_path \
        --segments "$CFG_VIDEO" "$CAT_VIDEO" "$RECEIPT_VIDEO" \
        --output "$FULL_PATH_VIDEO"
    log "Full-path video: ${FULL_PATH_VIDEO}"
else
    warn "Skipping full-path stitch (missing prerequisite videos)"
    [[ -f "$CFG_VIDEO" ]]     || warn "  Missing: $CFG_VIDEO"
    [[ -f "$CAT_VIDEO" ]]     || warn "  Missing: $CAT_VIDEO"
    [[ -f "$RECEIPT_VIDEO" ]] || warn "  Missing: $RECEIPT_VIDEO"
fi

exit 0
