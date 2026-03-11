#!/usr/bin/env bash
# =============================================================================
# build_userstories.sh — Rebuild the user stories site from scratch
#
# Usage:
#   ./build_userstories.sh                     # Full rebuild (artifacts + site)
#   ./build_userstories.sh --all               # Full rebuild (same as default)
#   ./build_userstories.sh --artifacts         # DAG diagrams + markdown only
#   ./build_userstories.sh --site              # Site generation only (needs artifacts)
#   ./build_userstories.sh --gifs              # Re-record all GIFs
#   ./build_userstories.sh --gifs-standalone   # Re-record self-contained GIFs only
#   ./build_userstories.sh --gifs-config       # Re-record config-dependent GIFs only
#   ./build_userstories.sh --gif <dir_name>    # Re-record a single GIF (e.g. 2b_label_receipt)
#   ./build_userstories.sh --serve [port]      # Build + serve (default port: 8059)
#   ./build_userstories.sh --serve-only [port] # Just serve (no rebuild, default port: 8059)
#   ./build_userstories.sh --help              # Show this help
#
# Options:
#   --output <dir>      Site output directory (default: /tmp/site)
#   --config <path>     Config file for GIFs that need it (auto-generated if omitted)
#   --dim-opacity <val> Opacity for non-used DAG nodes (0.0–1.0, default: 0.18)
#   --no-svg            Skip PlantUML SVG generation (use PNG fallbacks)
#   --no-render         Skip plantuml PNG rendering of artifacts
#   --dry-run           Show what would run without executing
#
# Modules:
#   artifacts   generate_userstory_artifacts.py -a --render
#   site        generate_site.py --output <dir>
#   gifs        All generate.sh scripts in gifs/*/
#
# Dependencies:
#   Required:  python3, PyYAML
#   Artifacts: plantuml (for --render and SVGs)
#   GIFs:      asciinema, asciinema-agg (agg), gifsicle, ffmpeg,
#              conda env "hledger_preprocessor" with project installed
# =============================================================================

set -euo pipefail

# ================================ Config =====================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DAG_DIR="$SCRIPT_DIR/user_stories/dag"
GIFS_DIR="$SCRIPT_DIR/gifs"
DEFAULT_OUTPUT="/tmp/site"
DEFAULT_PORT=8059

# ================================ Colors =====================================
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
RESET='\033[0m'

log()    { echo -e "${BOLD}${GREEN}[+]${RESET} $*"; }
warn()   { echo -e "${BOLD}${YELLOW}[!]${RESET} $*"; }
error()  { echo -e "${BOLD}${RED}[✗]${RESET} $*"; }
header() { echo -e "\n${CYAN}${BOLD}════════════════════════════════════════${RESET}"; \
           echo -e "${CYAN}${BOLD}  $1${RESET}"; \
           echo -e "${CYAN}${BOLD}════════════════════════════════════════${RESET}\n"; }

# ================================ Defaults ===================================
OUTPUT_DIR="$DEFAULT_OUTPUT"
CONFIG_PATH=""
DIM_OPACITY=""
SERVE_PORT=""
NO_SVG=""
NO_RENDER=""
DRY_RUN=""

# Modules to run
DO_ARTIFACTS=""
DO_SITE=""
DO_GIFS=""
DO_GIFS_STANDALONE=""
DO_GIFS_CONFIG=""
DO_SINGLE_GIF=""
SINGLE_GIF_DIR=""

# ================================ Help =======================================
show_help() {
    # Extract the header comment from this script
    sed -n '2,/^# =====/{ /^#/s/^# \?//p }' "$0"
    exit 0
}

# ================================ Arg Parsing ================================
parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --help|-h)     show_help ;;
            --all)         DO_ARTIFACTS=1; DO_SITE=1 ;;
            --artifacts)   DO_ARTIFACTS=1 ;;
            --site)        DO_SITE=1 ;;
            --gifs)        DO_GIFS=1 ;;
            --gifs-standalone) DO_GIFS_STANDALONE=1 ;;
            --gifs-config) DO_GIFS_CONFIG=1 ;;
            --gif)
                DO_SINGLE_GIF=1
                shift
                [[ $# -gt 0 ]] || { error "--gif requires a directory name"; exit 1; }
                SINGLE_GIF_DIR="$1"
                ;;
            --serve)
                DO_ARTIFACTS=1; DO_SITE=1
                if [[ "${2:-}" =~ ^[0-9]+$ ]]; then
                    SERVE_PORT="$2"; shift
                else
                    SERVE_PORT="$DEFAULT_PORT"
                fi
                ;;
            --serve-only)
                if [[ "${2:-}" =~ ^[0-9]+$ ]]; then
                    SERVE_PORT="$2"; shift
                else
                    SERVE_PORT="$DEFAULT_PORT"
                fi
                ;;
            --output)
                shift
                [[ $# -gt 0 ]] || { error "--output requires a path"; exit 1; }
                OUTPUT_DIR="$1"
                ;;
            --config)
                shift
                [[ $# -gt 0 ]] || { error "--config requires a path"; exit 1; }
                CONFIG_PATH="$1"
                ;;
            --dim-opacity)
                shift
                [[ $# -gt 0 ]] || { error "--dim-opacity requires a value (0.0–1.0)"; exit 1; }
                DIM_OPACITY="$1"
                ;;
            --no-svg)      NO_SVG=1 ;;
            --no-render)   NO_RENDER=1 ;;
            --dry-run)     DRY_RUN=1 ;;
            *)
                error "Unknown option: $1"
                echo "Run with --help for usage."
                exit 1
                ;;
        esac
        shift
    done

    # Default: --all (artifacts + site)
    if [[ -z "$DO_ARTIFACTS" && -z "$DO_SITE" && -z "$DO_GIFS" && \
          -z "$DO_GIFS_STANDALONE" && -z "$DO_GIFS_CONFIG" && -z "$DO_SINGLE_GIF" && \
          -z "$SERVE_PORT" ]]; then
        DO_ARTIFACTS=1
        DO_SITE=1
    fi
}

# ================================ Dependency Checks ==========================
check_deps() {
    local missing=()

    if ! command -v python3 &>/dev/null; then
        missing+=("python3")
    fi

    if [[ -n "$DO_ARTIFACTS" ]] && [[ -z "$NO_RENDER" ]]; then
        if ! command -v plantuml &>/dev/null; then
            warn "plantuml not found — artifacts will skip PNG rendering"
            NO_RENDER=1
        fi
    fi

    if [[ -n "$DO_GIFS" || -n "$DO_GIFS_STANDALONE" || -n "$DO_GIFS_CONFIG" || -n "$DO_SINGLE_GIF" ]]; then
        command -v asciinema &>/dev/null   || missing+=("asciinema")
        command -v gifsicle  &>/dev/null   || warn "gifsicle not found — GIF optimization will be skipped"
        command -v ffmpeg    &>/dev/null    || warn "ffmpeg not found — MP4 conversion will be skipped"

        # Check for agg (asciinema-agg)
        if ! command -v asciinema-agg &>/dev/null && ! command -v agg &>/dev/null; then
            missing+=("asciinema-agg (pip install agg)")
        fi
    fi

    if [[ ${#missing[@]} -gt 0 ]]; then
        error "Missing required dependencies: ${missing[*]}"
        exit 1
    fi
}

# ================================ Auto-Config =================================
DEFAULT_CONFIG="/tmp/hledger_demo/config.yaml"

ensure_config() {
    # If --config was given, use it as-is.
    if [[ -n "$CONFIG_PATH" ]]; then
        return
    fi

    # Auto-generate the demo environment (creates config + test data).
    log "No --config given — running setup_test_environment.py to generate demo data..."
    if [[ -n "$DRY_RUN" ]]; then
        warn "[dry-run] Would run: python -m gifs.automation.setup_test_environment"
        CONFIG_PATH="$DEFAULT_CONFIG"
        return
    fi

    cd "$SCRIPT_DIR"
    python -m gifs.automation.setup_test_environment
    CONFIG_PATH="$DEFAULT_CONFIG"
    log "Using auto-generated config: $CONFIG_PATH"
}

# ================================ Modules ====================================

run_artifacts() {
    header "Step 1: Generate DAG Artifacts"

    local flags=(-a)
    if [[ -z "$NO_RENDER" ]]; then
        flags+=(--render)
    fi

    log "Running: generate_userstory_artifacts.py ${flags[*]}"

    if [[ -n "$DRY_RUN" ]]; then
        warn "[dry-run] Would run: python3 $DAG_DIR/generate_userstory_artifacts.py ${flags[*]}"
        return
    fi

    cd "$DAG_DIR"
    python3 generate_userstory_artifacts.py "${flags[@]}"
    log "Artifacts generated in $DAG_DIR/output/"
}


run_site() {
    header "Step 2: Generate Static Site"

    local flags=(--output "$OUTPUT_DIR")
    if [[ -n "$NO_SVG" ]]; then
        flags+=(--no-svg)
    fi
    if [[ -n "$DIM_OPACITY" ]]; then
        flags+=(--dim-opacity "$DIM_OPACITY")
    fi

    log "Running: generate_site.py ${flags[*]}"

    if [[ -n "$DRY_RUN" ]]; then
        warn "[dry-run] Would run: python3 $DAG_DIR/generate_site.py ${flags[*]}"
        return
    fi

    cd "$DAG_DIR"
    python3 generate_site.py "${flags[@]}"
    log "Site generated at $OUTPUT_DIR/"
}


# GIF scripts that are self-contained (no config path needed)
STANDALONE_GIFS=(
    1a_setup_config
    1b_add_category
    2a_crop_receipt
    2b_label_foreign_currency
    2b_label_split_payment
    2b_label_returned_items
    3_match_receipt_to_csv
    3b_foreign_currency_match
    3c_widen_date_match
    3d_disambiguate_match
)

# GIF scripts that require a config path (use init_demo / common.sh)
CONFIG_GIFS=(
    2b_label_receipt
    4_run_pipeline
    5_show_plots
)

run_single_gif() {
    local dir_name="$1"
    local gen_script="$GIFS_DIR/$dir_name/generate.sh"

    if [[ ! -f "$gen_script" ]]; then
        error "No generate.sh found in gifs/$dir_name/"
        return 1
    fi

    log "Recording GIF: $dir_name"

    # Determine if this script needs a config path
    local needs_config=""
    for cfg_gif in "${CONFIG_GIFS[@]}"; do
        if [[ "$dir_name" == "$cfg_gif" ]]; then
            needs_config=1
            break
        fi
    done

    if [[ -n "$needs_config" ]]; then
        ensure_config
    fi

    if [[ -n "$DRY_RUN" ]]; then
        if [[ -n "$needs_config" ]]; then
            warn "[dry-run] Would run: bash $gen_script $CONFIG_PATH"
        else
            warn "[dry-run] Would run: bash $gen_script"
        fi
        return
    fi

    cd "$SCRIPT_DIR"
    if [[ -n "$needs_config" ]]; then
        bash "$gen_script" "$CONFIG_PATH"
    else
        bash "$gen_script"
    fi
}


run_gifs_standalone() {
    header "GIF Generation: Self-Contained Demos"

    local count=0
    local failed=0

    for dir_name in "${STANDALONE_GIFS[@]}"; do
        local gen_script="$GIFS_DIR/$dir_name/generate.sh"
        if [[ ! -f "$gen_script" ]]; then
            warn "Skipping $dir_name (no generate.sh)"
            continue
        fi

        log "[$((count + 1))/${#STANDALONE_GIFS[@]}] Recording: $dir_name"

        if [[ -n "$DRY_RUN" ]]; then
            warn "[dry-run] Would run: bash $gen_script"
        else
            cd "$SCRIPT_DIR"
            if bash "$gen_script"; then
                log "  Done: $dir_name"
            else
                warn "  Failed: $dir_name (continuing)"
                ((failed++)) || true
            fi
        fi
        ((count++)) || true
    done

    log "Standalone GIFs: $count attempted, $failed failed"
}


run_gifs_config() {
    header "GIF Generation: Config-Dependent Demos"

    ensure_config

    if [[ ! -f "$CONFIG_PATH" ]]; then
        error "Config file not found: $CONFIG_PATH"
        exit 1
    fi

    local count=0
    local failed=0

    for dir_name in "${CONFIG_GIFS[@]}"; do
        local gen_script="$GIFS_DIR/$dir_name/generate.sh"
        if [[ ! -f "$gen_script" ]]; then
            warn "Skipping $dir_name (no generate.sh)"
            continue
        fi

        log "[$((count + 1))/${#CONFIG_GIFS[@]}] Recording: $dir_name"

        if [[ -n "$DRY_RUN" ]]; then
            warn "[dry-run] Would run: bash $gen_script $CONFIG_PATH"
        else
            cd "$SCRIPT_DIR"
            if bash "$gen_script" "$CONFIG_PATH"; then
                log "  Done: $dir_name"
            else
                warn "  Failed: $dir_name (continuing)"
                ((failed++)) || true
            fi
        fi
        ((count++)) || true
    done

    log "Config-dependent GIFs: $count attempted, $failed failed"
}


run_serve() {
    header "Serving Site"

    if [[ -n "$DRY_RUN" ]]; then
        warn "[dry-run] Would serve: http://localhost:${SERVE_PORT}/ from $OUTPUT_DIR"
        return
    fi

    # Kill any existing process on the target port
    local existing_pid
    existing_pid=$(ss -tlnp "sport = :${SERVE_PORT}" 2>/dev/null \
        | awk 'NR>1 { match($0, /pid=([0-9]+)/, m); if (m[1]) print m[1] }')
    if [[ -n "$existing_pid" ]]; then
        warn "Port ${SERVE_PORT} already in use (pid $existing_pid) — killing it"
        kill "$existing_pid" 2>/dev/null || true
        sleep 0.5
    fi

    log "URL: http://localhost:${SERVE_PORT}/"
    log "Press Ctrl+C to stop"
    echo
    python3 -m http.server "$SERVE_PORT" --directory "$OUTPUT_DIR"
}

# ================================ Main =======================================

main() {
    parse_args "$@"
    check_deps

    echo -e "${BOLD}hledger-preprocessor: User Stories Site Builder${RESET}"
    echo -e "Output: ${OUTPUT_DIR}"
    echo

    # Run selected modules
    [[ -n "$DO_ARTIFACTS" ]]        && run_artifacts
    [[ -n "$DO_GIFS" ]]             && { run_gifs_standalone; [[ -n "$CONFIG_PATH" ]] && run_gifs_config || warn "Skipping config-dependent GIFs (no --config given)"; }
    [[ -n "$DO_GIFS_STANDALONE" ]]  && run_gifs_standalone
    [[ -n "$DO_GIFS_CONFIG" ]]      && run_gifs_config
    [[ -n "$DO_SINGLE_GIF" ]]       && run_single_gif "$SINGLE_GIF_DIR"
    [[ -n "$DO_SITE" ]]             && run_site

    if [[ -n "$SERVE_PORT" ]]; then
        run_serve
    elif [[ -n "$DO_SITE" ]]; then
        SERVE_PORT="$DEFAULT_PORT"
        run_serve
    fi
}

main "$@"
