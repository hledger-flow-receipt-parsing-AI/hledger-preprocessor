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
#
# Marker IDs use the config sublevel node IDs from userstory_dag_data.yaml:
#   acct_triodos_csv, acct_ing_csv, acct_eur_wallet, etc. (config_accounts)
#   dirp_default (config_dir_paths)
#   fnames_default (config_file_names)
#   catcfg_default (config_categorisation)
#   malgo_default (config_matching_algo)
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
#   NODE_ID:   e.g. cfg_1b (used as output filename stem)
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
    "${ACCTS}/triodos.yaml=acct_triodos_csv" \
    "${SHARED}/dir_paths.yaml=dirp_default" \
    "${SHARED}/file_names.yaml=fnames_default" \
    "${SHARED}/categorisation.yaml=catcfg_default" \
    "${SHARED}/matching_algo.yaml=malgo_default"

# ---------------------------------------------------------------------------
# cfg_2b: 2 banks (Triodos + ING)
# ---------------------------------------------------------------------------
generate_gif cfg_2b \
    "${ACCTS}/triodos.yaml=acct_triodos_csv" \
    "${ACCTS}/ing.yaml=acct_ing_csv" \
    "${SHARED}/dir_paths.yaml=dirp_default" \
    "${SHARED}/file_names.yaml=fnames_default" \
    "${SHARED}/categorisation.yaml=catcfg_default" \
    "${SHARED}/matching_algo.yaml=malgo_default"

# ---------------------------------------------------------------------------
# cfg_1w: 1 wallet (EUR cash)
# ---------------------------------------------------------------------------
generate_gif cfg_1w \
    "${ACCTS}/eur_wallet_first.yaml=acct_eur_wallet" \
    "${SHARED}/dir_paths.yaml=dirp_default" \
    "${SHARED}/file_names.yaml=fnames_default" \
    "${SHARED}/categorisation.yaml=catcfg_default"

# ---------------------------------------------------------------------------
# cfg_crypto: Triodos + BTC wallet
# ---------------------------------------------------------------------------
generate_gif cfg_crypto \
    "${ACCTS}/triodos.yaml=acct_triodos_csv" \
    "${ACCTS}/btc_wallet.yaml=acct_btc_wallet" \
    "${SHARED}/dir_paths.yaml=dirp_default" \
    "${SHARED}/file_names.yaml=fnames_default" \
    "${SHARED}/categorisation.yaml=catcfg_default" \
    "${SHARED}/matching_algo.yaml=malgo_default"

# ---------------------------------------------------------------------------
# cfg_per_bank_match: Triodos + ING + EUR wallet
# ---------------------------------------------------------------------------
generate_gif cfg_per_bank_match \
    "${ACCTS}/triodos.yaml=acct_triodos_csv" \
    "${ACCTS}/ing.yaml=acct_ing_csv" \
    "${ACCTS}/eur_wallet.yaml=acct_eur_wallet" \
    "${SHARED}/dir_paths.yaml=dirp_default" \
    "${SHARED}/file_names.yaml=fnames_default" \
    "${SHARED}/categorisation.yaml=catcfg_default" \
    "${SHARED}/matching_algo.yaml=malgo_default"

# ---------------------------------------------------------------------------
# cfg_1b5a: Triodos + 5 wallets (EUR/GBP/BTC/GOLD/SILVER)
# ---------------------------------------------------------------------------
generate_gif cfg_1b5a \
    "${ACCTS}/triodos.yaml=acct_triodos_csv" \
    "${ACCTS}/eur_wallet.yaml=acct_eur_wallet" \
    "${ACCTS}/gbp_wallet.yaml=acct_gbp_wallet" \
    "${ACCTS}/btc_wallet.yaml=acct_btc_wallet" \
    "${ACCTS}/gold_wallet.yaml=acct_gold_wallet" \
    "${ACCTS}/silver_wallet.yaml=acct_silver_wallet" \
    "${SHARED}/dir_paths.yaml=dirp_default" \
    "${SHARED}/file_names.yaml=fnames_default" \
    "${SHARED}/categorisation.yaml=catcfg_default" \
    "${SHARED}/matching_algo.yaml=malgo_default"

# ---------------------------------------------------------------------------
# cfg_1b1w: Triodos + EUR wallet
# ---------------------------------------------------------------------------
generate_gif cfg_1b1w \
    "${ACCTS}/triodos.yaml=acct_triodos_csv" \
    "${ACCTS}/eur_wallet.yaml=acct_eur_wallet" \
    "${SHARED}/dir_paths.yaml=dirp_default" \
    "${SHARED}/file_names.yaml=fnames_default" \
    "${SHARED}/categorisation.yaml=catcfg_default" \
    "${SHARED}/matching_algo.yaml=malgo_default"

# ---------------------------------------------------------------------------
# cfg_merge: Kraken (multi-row merge) + Bitvavo (atomic) + Triodos
# ---------------------------------------------------------------------------
generate_gif cfg_merge \
    "${ACCTS}/kraken.yaml=acct_kraken_csv" \
    "${ACCTS}/bitvavo.yaml=acct_bitvavo_csv" \
    "${ACCTS}/triodos.yaml=acct_triodos_csv" \
    "${SHARED}/dir_paths.yaml=dirp_default" \
    "${SHARED}/file_names.yaml=fnames_default" \
    "${SHARED}/categorisation.yaml=catcfg_default" \
    "${SHARED}/matching_algo.yaml=malgo_default"

log "All config GIFs generated!"
exit 0
