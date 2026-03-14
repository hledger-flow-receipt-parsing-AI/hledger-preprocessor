#!/usr/bin/env bash
# =============================================================================
# Data File Segments - GIF Generator
#
# Generates typing-animation GIFs for the data file nodes that appear in the
# full-path DAG of US-2b.1 (and other stories):
#   - starting_journal: opening balance journal entry
#   - bank_csv:         Triodos CSV transaction
#   - journal_output:   final double-entry journal posting
#
# Uses yaml_typing_gif.py --segments to produce per-section markers.
# =============================================================================

set -euo pipefail

# ================================ Config =====================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
OUTPUT_DIR="${SCRIPT_DIR}/output"
DATA_DIR="${PROJECT_ROOT}/test/fixtures/config_fragments/data_files"

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

if [[ ! -d "$DATA_DIR" ]]; then
    echo "Error: Data files directory not found: $DATA_DIR"
    exit 1
fi

export PYTHONPATH="${PROJECT_ROOT}:${PYTHONPATH:-}"

# ---------------------------------------------------------------------------
# start_journal: Opening balance journal
# ---------------------------------------------------------------------------
log "Generating starting_journal typing animation..."
python -m gifs.automation.yaml_typing_gif \
    --segments \
        "${DATA_DIR}/starting_journal_1000eur.journal=start_2024_1000eur" \
    --output "${OUTPUT_DIR}/starting_journal.gif" \
    --markers-output "${OUTPUT_DIR}/starting_journal_markers.json" \
    --title "2024-opening.journal" \
    --rows 35 \
    --cols 85
convert_gif_to_mp4 "${OUTPUT_DIR}/starting_journal.gif"

# ---------------------------------------------------------------------------
# bank_csv: Triodos CSV transaction
# ---------------------------------------------------------------------------
log "Generating bank_csv typing animation..."
python -m gifs.automation.yaml_typing_gif \
    --segments \
        "${DATA_DIR}/csv_ekoplaza_4217.csv=csv_ekoplaza_4217_jan15" \
    --output "${OUTPUT_DIR}/bank_csv.gif" \
    --markers-output "${OUTPUT_DIR}/bank_csv_markers.json" \
    --title "triodos-checking-2025.csv" \
    --rows 35 \
    --cols 85
convert_gif_to_mp4 "${OUTPUT_DIR}/bank_csv.gif"

# ---------------------------------------------------------------------------
# journal_output: Final journal posting
# ---------------------------------------------------------------------------
log "Generating journal_output typing animation..."
python -m gifs.automation.yaml_typing_gif \
    --segments \
        "${DATA_DIR}/journal_groceries_ekoplaza.journal=jrnl_groceries_ekoplaza" \
    --output "${OUTPUT_DIR}/journal_output.gif" \
    --markers-output "${OUTPUT_DIR}/journal_output_markers.json" \
    --title "triodos-checking.journal" \
    --rows 35 \
    --cols 85
convert_gif_to_mp4 "${OUTPUT_DIR}/journal_output.gif"

# ---------------------------------------------------------------------------
# bank_csv_atm_gbp: ATM GBP withdrawal CSV for US-2b.3
# ---------------------------------------------------------------------------
log "Generating bank_csv_atm_gbp typing animation..."
python -m gifs.automation.yaml_typing_gif \
    --segments \
        "${DATA_DIR}/csv_atm_gbp_11750.csv=csv_atm_gbp_11750" \
    --output "${OUTPUT_DIR}/bank_csv_atm_gbp.gif" \
    --markers-output "${OUTPUT_DIR}/bank_csv_atm_gbp_markers.json" \
    --title "triodos-checking-2025.csv" \
    --rows 35 \
    --cols 85
convert_gif_to_mp4 "${OUTPUT_DIR}/bank_csv_atm_gbp.gif"

# ---------------------------------------------------------------------------
# bank_csv_split_dinner: Split dinner CSV for US-2b.4
# ---------------------------------------------------------------------------
log "Generating bank_csv_split_dinner typing animation..."
python -m gifs.automation.yaml_typing_gif \
    --segments \
        "${DATA_DIR}/csv_split_dinner_30.csv=csv_split_dinner_30" \
    --output "${OUTPUT_DIR}/bank_csv_split_dinner.gif" \
    --markers-output "${OUTPUT_DIR}/bank_csv_split_dinner_markers.json" \
    --title "triodos-checking-2025.csv" \
    --rows 35 \
    --cols 85
convert_gif_to_mp4 "${OUTPUT_DIR}/bank_csv_split_dinner.gif"

# ---------------------------------------------------------------------------
# journal_output_atm_gbp: ATM GBP journal for US-2b.3
# ---------------------------------------------------------------------------
log "Generating journal_output_atm_gbp typing animation..."
python -m gifs.automation.yaml_typing_gif \
    --segments \
        "${DATA_DIR}/journal_atm_gbp.journal=jrnl_wallet_gbp" \
    --output "${OUTPUT_DIR}/journal_output_atm_gbp.gif" \
    --markers-output "${OUTPUT_DIR}/journal_output_atm_gbp_markers.json" \
    --title "triodos-checking.journal" \
    --rows 35 \
    --cols 85
convert_gif_to_mp4 "${OUTPUT_DIR}/journal_output_atm_gbp.gif"

# ---------------------------------------------------------------------------
# journal_output_split_dinner: Split dinner journal for US-2b.4
# ---------------------------------------------------------------------------
log "Generating journal_output_split_dinner typing animation..."
python -m gifs.automation.yaml_typing_gif \
    --segments \
        "${DATA_DIR}/journal_split_dinner.journal=jrnl_dinner_split_card" \
    --output "${OUTPUT_DIR}/journal_output_split_dinner.gif" \
    --markers-output "${OUTPUT_DIR}/journal_output_split_dinner_markers.json" \
    --title "triodos-checking.journal" \
    --rows 35 \
    --cols 85
convert_gif_to_mp4 "${OUTPUT_DIR}/journal_output_split_dinner.gif"

# ---------------------------------------------------------------------------
# journal_output_return_net: Returned items journal for US-2b.5
# ---------------------------------------------------------------------------
log "Generating journal_output_return_net typing animation..."
python -m gifs.automation.yaml_typing_gif \
    --segments \
        "${DATA_DIR}/journal_return_net.journal=jrnl_return_net" \
    --output "${OUTPUT_DIR}/journal_output_return_net.gif" \
    --markers-output "${OUTPUT_DIR}/journal_output_return_net_markers.json" \
    --title "triodos-checking.journal" \
    --rows 35 \
    --cols 85
convert_gif_to_mp4 "${OUTPUT_DIR}/journal_output_return_net.gif"

log "All data file GIFs generated!"
exit 0
