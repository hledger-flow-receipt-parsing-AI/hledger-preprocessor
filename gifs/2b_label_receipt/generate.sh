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

# ── Step 2: Stitch full-path video for US-2b.1 ───────────────────────
if [[ "${SKIP_STITCH:-0}" == "1" ]]; then
    log "Skipping stitch step (SKIP_STITCH=1)"
else
GIFS_ROOT="${SCRIPT_DIR}/.."
CFG_VIDEO="${GIFS_ROOT}/1a_setup_config/output/cfg_1b1w.mp4"
CAT_VIDEO="${GIFS_ROOT}/1b_add_category/output/cat_basic.mp4"
STARTJ_VIDEO="${GIFS_ROOT}/2b_data_files/output/starting_journal.mp4"
CSV_VIDEO="${GIFS_ROOT}/2b_data_files/output/bank_csv.mp4"
RECEIPT_VIDEO="${OUTPUT_DIR}/2b_label_receipt_dracula.mp4"
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
