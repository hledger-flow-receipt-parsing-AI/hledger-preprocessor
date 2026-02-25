#!/usr/bin/env bash
# =============================================================================
# Setup Config Demo - GIF Generator
#
# Generates one GIF per config node variant (cfg_1b, cfg_2b, cfg_1w, etc.)
# Each GIF types the matching account fragments + shared config sections.
# Uses yaml_typing_gif.py --segments to record per-section timestamps.
#
# Each account in a multi-account config gets its own segment so the site
# can show per-account clickable nodes with accurate timestamps.
# =============================================================================

set -euo pipefail

# ================================ Config =====================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
OUTPUT_DIR="${SCRIPT_DIR}/output"
FRAG_DIR="${PROJECT_ROOT}/test/fixtures/config_fragments"
SHARED="${FRAG_DIR}/shared"
ACCTS="${FRAG_DIR}/accounts/per_account"

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

# generate_gif NODE_ID SEGMENTS...
#   NODE_ID:   e.g. cfg_1b
#   SEGMENTS:  "filepath=marker_id" pairs
generate_gif() {
    local node_id="$1"
    shift
    local segments=("$@")

    local gif_file="${OUTPUT_DIR}/${node_id}.gif"
    local markers_file="${OUTPUT_DIR}/${node_id}_markers.json"

    log "Generating ${node_id} config typing animation..."

    python -m gifs.automation.yaml_typing_gif \
        --segments "${segments[@]}" \
        --output "$gif_file" \
        --markers-output "$markers_file" \
        --title "config.yaml" \
        --rows 35 \
        --cols 85

    log "  GIF: $gif_file"
    log "  Markers: $markers_file"

    convert_gif_to_mp4 "$gif_file"
}

# ================================ Main =======================================

mkdir -p "$OUTPUT_DIR"

if [[ ! -d "$FRAG_DIR" ]]; then
    echo "Error: Config fragments directory not found: $FRAG_DIR"
    exit 1
fi

export PYTHONPATH="${PROJECT_ROOT}:${PYTHONPATH:-}"

# ---------------------------------------------------------------------------
# cfg_1b: 1 bank (Triodos)
# ---------------------------------------------------------------------------
generate_gif cfg_1b \
    "${ACCTS}/triodos.yaml=cfg_1b__triodos_csv" \
    "${SHARED}/dir_paths.yaml=cfg_1b__dir_paths" \
    "${SHARED}/file_names.yaml=cfg_1b__file_names" \
    "${SHARED}/categorisation.yaml=cfg_1b__categorisation" \
    "${SHARED}/matching_algo.yaml=cfg_1b__matching_algo"

# ---------------------------------------------------------------------------
# cfg_2b: 2 banks (Triodos + ING)
# ---------------------------------------------------------------------------
generate_gif cfg_2b \
    "${ACCTS}/triodos.yaml=cfg_2b__triodos_csv" \
    "${ACCTS}/ing.yaml=cfg_2b__ing_csv" \
    "${SHARED}/dir_paths.yaml=cfg_2b__dir_paths" \
    "${SHARED}/file_names.yaml=cfg_2b__file_names" \
    "${SHARED}/categorisation.yaml=cfg_2b__categorisation" \
    "${SHARED}/matching_algo.yaml=cfg_2b__matching_algo"

# ---------------------------------------------------------------------------
# cfg_1w: 1 wallet (EUR cash)
# ---------------------------------------------------------------------------
generate_gif cfg_1w \
    "${ACCTS}/eur_wallet_first.yaml=cfg_1w__eur_wallet" \
    "${SHARED}/dir_paths.yaml=cfg_1w__dir_paths" \
    "${SHARED}/file_names.yaml=cfg_1w__file_names" \
    "${SHARED}/categorisation.yaml=cfg_1w__categorisation"

# ---------------------------------------------------------------------------
# cfg_crypto: Triodos + BTC wallet
# ---------------------------------------------------------------------------
generate_gif cfg_crypto \
    "${ACCTS}/triodos.yaml=cfg_crypto__triodos_csv" \
    "${ACCTS}/btc_wallet.yaml=cfg_crypto__btc_wallet" \
    "${SHARED}/dir_paths.yaml=cfg_crypto__dir_paths" \
    "${SHARED}/file_names.yaml=cfg_crypto__file_names" \
    "${SHARED}/categorisation.yaml=cfg_crypto__categorisation" \
    "${SHARED}/matching_algo.yaml=cfg_crypto__matching_algo"

# ---------------------------------------------------------------------------
# cfg_per_bank_match: Triodos + ING + EUR wallet
# ---------------------------------------------------------------------------
generate_gif cfg_per_bank_match \
    "${ACCTS}/triodos.yaml=cfg_per_bank_match__triodos_csv" \
    "${ACCTS}/ing.yaml=cfg_per_bank_match__ing_csv" \
    "${ACCTS}/eur_wallet.yaml=cfg_per_bank_match__eur_wallet" \
    "${SHARED}/dir_paths.yaml=cfg_per_bank_match__dir_paths" \
    "${SHARED}/file_names.yaml=cfg_per_bank_match__file_names" \
    "${SHARED}/categorisation.yaml=cfg_per_bank_match__categorisation" \
    "${SHARED}/matching_algo.yaml=cfg_per_bank_match__matching_algo"

# ---------------------------------------------------------------------------
# cfg_1b5a: Triodos + 5 wallets (EUR/GBP/BTC/GOLD/SILVER)
# ---------------------------------------------------------------------------
generate_gif cfg_1b5a \
    "${ACCTS}/triodos.yaml=cfg_1b5a__triodos_csv" \
    "${ACCTS}/eur_wallet.yaml=cfg_1b5a__eur_wallet" \
    "${ACCTS}/gbp_wallet.yaml=cfg_1b5a__gbp_wallet" \
    "${ACCTS}/btc_wallet.yaml=cfg_1b5a__btc_wallet" \
    "${ACCTS}/gold_wallet.yaml=cfg_1b5a__gold_wallet" \
    "${ACCTS}/silver_wallet.yaml=cfg_1b5a__silver_wallet" \
    "${SHARED}/dir_paths.yaml=cfg_1b5a__dir_paths" \
    "${SHARED}/file_names.yaml=cfg_1b5a__file_names" \
    "${SHARED}/categorisation.yaml=cfg_1b5a__categorisation" \
    "${SHARED}/matching_algo.yaml=cfg_1b5a__matching_algo"

log "All config GIFs generated!"
exit 0
