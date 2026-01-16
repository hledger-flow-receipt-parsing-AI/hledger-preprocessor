#!/usr/bin/env bash
# =============================================================================
# Common utilities for GIF generation scripts
# Source this file from individual demo scripts
#
# Usage in demo scripts:
#   SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
#   source "${SCRIPT_DIR}/../scripts/common.sh"
#
#   # Then call: init_demo "demo_name" "$@"
# =============================================================================

# Don't set -e here, let the sourcing script decide
set -uo pipefail

# ================================ Colors =====================================
RED="$(tput setaf 1 2>/dev/null || echo '')"
GREEN="$(tput setaf 2 2>/dev/null || echo '')"
YELLOW="$(tput setaf 3 2>/dev/null || echo '')"
BLUE="$(tput setaf 4 2>/dev/null || echo '')"
PURPLE="$(tput setaf 5 2>/dev/null || echo '')"
CYAN="$(tput setaf 6 2>/dev/null || echo '')"
BOLD="$(tput bold 2>/dev/null || echo '')"
RESET="$(tput sgr0 2>/dev/null || echo '')"

# ================================ Logging ====================================
log()    { echo -e "${BOLD}${GREEN}[+]${RESET} $*" ; }
warn()   { echo -e "${BOLD}${YELLOW}[!]${RESET} $*" ; }
error()  { echo -e "${BOLD}${RED}[✗]${RESET} $*" ; }
header() { echo -e "${PURPLE}${BOLD}=== $1 ===${RESET}" ; }
debug()  { [[ "${DEBUG:-0}" == "1" ]] && echo -e "${CYAN}[D]${RESET} $*" ; }

# ================================ Themes =====================================
# Format: "name:theme_value"
# Built-in themes: asciinema, dracula, monokai, solarized-dark, solarized-light
# Custom themes: comma-separated hex colors (bg,fg,black,red,green,yellow,blue,magenta,cyan,white)
declare -a DEFAULT_THEMES=(
    "dracula:dracula"
    "monokai:monokai"
    "solarized-dark:solarized-dark"
    "solarized-light:solarized-light"
    "amber:0a0a0a,ffb000,1a1a1a,cc4400,ff8800,ffb000,ff6600,cc6600,ffcc00,ffdd88"
    "green-phosphor:0a0a0a,33ff33,1a1a1a,00cc00,33ff33,66ff66,00aa00,009900,99ff99,ccffcc"
    "cyan-cool:0a0f14,00ffff,0a1a1f,ff6666,66ffcc,ffff66,6699ff,ff66ff,00ffff,ffffff"
    "matrix:000000,00ff00,0a0a0a,ff0000,00ff00,ffff00,0066ff,ff00ff,00ffff,ffffff"
)

# ================================ Defaults ===================================
DEFAULT_ROWS=50
DEFAULT_COLS=120
DEFAULT_IDLE_TIME_LIMIT=2
DEFAULT_FONT_SIZE=20

# ================================ Global State ===============================
# These are set by init_demo and used throughout
DEMO_NAME=""
DEMO_DIR=""
OUTPUT_DIR=""
RECORDINGS_DIR=""
CAST_FILE=""
OUTPUT_GIF=""
SHOWCASE_GIF=""
PROJECT_ROOT=""

# Array to track generated GIFs (populated by generate_themed_gifs)
declare -a GENERATED_GIFS=()

# ================================ Pre-flight Checks ==========================

check_conda_env() {
    local expected_env="${1:-hledger_preprocessor}"
    if [[ "$(python -c 'import sys; print(sys.executable)' 2>/dev/null || echo '')" != */"${expected_env}"/* ]]; then
        error "Not in the '${expected_env}' conda environment!"
        warn "Please run: conda activate ${expected_env}"
        return 1
    fi
    return 0
}

check_gifsicle() {
    if ! command -v gifsicle >/dev/null 2>&1; then
        error "gifsicle not found!"
        warn "Install with: sudo apt install gifsicle"
        return 1
    fi
    return 0
}

check_asciinema() {
    if ! command -v asciinema >/dev/null 2>&1; then
        error "asciinema not found!"
        warn "Install with: pip install asciinema"
        return 1
    fi
    return 0
}

check_agg() {
    if ! command -v asciinema-agg >/dev/null 2>&1; then
        log "Installing agg (asciinema → GIF converter)..."
        pip install -q agg || { error "Failed to install agg"; return 1; }
    fi
    return 0
}

run_preflight_checks() {
    check_conda_env || exit 1
    check_gifsicle || exit 1
    check_asciinema || exit 1
    check_agg || exit 1
}

# ================================ Initialization =============================

init_demo() {
    # Initialize demo environment
    # Usage: init_demo "demo_name" "$@"
    #   demo_name: Name of the demo (e.g., "edit_receipt", "label_transactions")
    #   $@: Script arguments (expects config path as first arg)

    local demo_name="$1"
    shift

    # Require config path
    if [[ $# -lt 1 ]]; then
        error "Missing config file path argument."
        echo "Usage: $0 <config_path>"
        exit 1
    fi

    local config_path="$1"
    export CONFIG_FILEPATH="$config_path"

    # Set global variables
    DEMO_NAME="$demo_name"
    DEMO_DIR="$(cd "$(dirname "${BASH_SOURCE[1]}")" && pwd)"
    PROJECT_ROOT="$(cd "$DEMO_DIR/../.." && pwd)"
    OUTPUT_DIR="${DEMO_DIR}/output"
    RECORDINGS_DIR="${DEMO_DIR}/recordings"
    CAST_FILE="${RECORDINGS_DIR}/${demo_name}.cast"
    OUTPUT_GIF="${OUTPUT_DIR}/${demo_name}.gif"
    SHOWCASE_GIF="${OUTPUT_DIR}/${demo_name}_showcase.gif"

    # Ensure directories exist
    mkdir -p "$OUTPUT_DIR" "$RECORDINGS_DIR"

    # Run preflight checks
    header "hledger-preprocessor: ${demo_name} demo"
    run_preflight_checks

    log "Demo: ${DEMO_NAME}"
    log "Config: ${CONFIG_FILEPATH}"
    log "Output: ${OUTPUT_DIR}"
}

# ================================ Recording ==================================

record_demo() {
    # Record a demo using asciinema
    # Usage: record_demo <python_module> [title] [rows] [cols] [idle_time_limit]

    local python_module="$1"
    local title="${2:-hledger-preprocessor ${DEMO_NAME} demo}"
    local rows="${3:-$DEFAULT_ROWS}"
    local cols="${4:-$DEFAULT_COLS}"
    local idle_time_limit="${5:-$DEFAULT_IDLE_TIME_LIMIT}"

    header "Recording: ${title}"

    # Remove old cast file
    rm -f "$CAST_FILE"

    if asciinema rec "$CAST_FILE" \
        --command="python -m ${python_module}" \
        --title "$title" \
        --idle-time-limit="$idle_time_limit" \
        --rows "$rows" \
        --cols "$cols" \
        --env="CONFIG_FILEPATH,PYTHONPATH" \
        -y -q; then
        log "Recording completed → ${CAST_FILE}"
        return 0
    else
        error "Recording failed!"
        return 1
    fi
}

# ================================ Post-processing ============================

postprocess_cast() {
    # Post-process the cast file to clean up escape sequences
    # Usage: postprocess_cast [cast_file]

    local cast_file="${1:-$CAST_FILE}"

    log "Post-processing cast file..."
    CAST_FILE="$cast_file" python -m gifs.automation.cast_postprocess
}

# ================================ GIF Generation =============================

generate_themed_gifs() {
    # Generate GIFs for all themes
    # Usage: generate_themed_gifs [font_size]

    local font_size="${1:-$DEFAULT_FONT_SIZE}"

    header "Generating themed GIFs (${#DEFAULT_THEMES[@]} themes)..."

    # Reset generated GIFs array
    GENERATED_GIFS=()

    # Remove old themed GIFs
    rm -f "${OUTPUT_DIR}/${DEMO_NAME}_"*.gif

    for theme_entry in "${DEFAULT_THEMES[@]}"; do
        local theme_name="${theme_entry%%:*}"
        local theme_value="${theme_entry#*:}"
        local output_file="${OUTPUT_DIR}/${DEMO_NAME}_${theme_name}.gif"

        log "  Generating ${theme_name}..."

        if asciinema-agg "$CAST_FILE" "$output_file" \
            --theme "$theme_value" \
            --font-size "$font_size" \
            --renderer resvg \
            --line-height 1.2 2>/dev/null; then
            GENERATED_GIFS+=("$output_file")
            debug "    → ${output_file}"
        else
            warn "    Failed to generate ${theme_name}, skipping..."
        fi
    done

    log "Generated ${#GENERATED_GIFS[@]} theme variants"
}

generate_single_gif() {
    # Generate a single GIF with a specific theme
    # Usage: generate_single_gif [theme_name] [font_size]

    local theme_name="${1:-dracula}"
    local font_size="${2:-$DEFAULT_FONT_SIZE}"
    local theme_value=""

    # Find theme value
    for theme_entry in "${DEFAULT_THEMES[@]}"; do
        if [[ "${theme_entry%%:*}" == "$theme_name" ]]; then
            theme_value="${theme_entry#*:}"
            break
        fi
    done

    if [[ -z "$theme_value" ]]; then
        error "Unknown theme: ${theme_name}"
        return 1
    fi

    log "Generating ${theme_name} GIF..."

    if asciinema-agg "$CAST_FILE" "$OUTPUT_GIF" \
        --theme "$theme_value" \
        --font-size "$font_size" \
        --renderer resvg \
        --line-height 1.2; then
        log "  → ${OUTPUT_GIF}"
        return 0
    else
        error "Failed to generate GIF"
        return 1
    fi
}

# ================================ Showcase ===================================

create_showcase() {
    # Combine all themed GIFs into a showcase
    # Usage: create_showcase

    if [[ ${#GENERATED_GIFS[@]} -eq 0 ]]; then
        warn "No GIFs to combine into showcase"
        return 1
    fi

    header "Creating showcase..."

    gifsicle --merge "${GENERATED_GIFS[@]}" -o "$SHOWCASE_GIF"

    log "Showcase: ${SHOWCASE_GIF} ($(du -h "$SHOWCASE_GIF" | cut -f1))"
}

set_default_gif() {
    # Set the default GIF (copy first themed GIF or specify one)
    # Usage: set_default_gif [source_gif]

    local source_gif="${1:-${GENERATED_GIFS[0]:-}}"

    if [[ -z "$source_gif" || ! -f "$source_gif" ]]; then
        error "No source GIF available for default"
        return 1
    fi

    cp "$source_gif" "$OUTPUT_GIF"
    log "Default GIF: ${OUTPUT_GIF} (from $(basename "$source_gif"))"
}

optimize_gif() {
    # Optimize a GIF using gifsicle (lossless)
    # Usage: optimize_gif [gif_file]

    local gif_file="${1:-$OUTPUT_GIF}"

    log "Optimizing $(basename "$gif_file")..."
    gifsicle -O3 -o "${gif_file}.tmp" "$gif_file" && mv "${gif_file}.tmp" "$gif_file"
    log "  Size: $(du -h "$gif_file" | cut -f1)"
}

# ================================ Summary ====================================

print_summary() {
    # Print a summary of generated files
    # Usage: print_summary

    local demo_path="gifs/${DEMO_NAME}"

    echo
    header "Summary"
    echo

    if [[ ${#GENERATED_GIFS[@]} -gt 0 ]]; then
        log "Theme variants:"
        for gif in "${GENERATED_GIFS[@]}"; do
            echo "   - $(basename "$gif") ($(du -h "$gif" | cut -f1))"
        done
        echo
    fi

    if [[ -f "$SHOWCASE_GIF" ]]; then
        log "Showcase: $(basename "$SHOWCASE_GIF") ($(du -h "$SHOWCASE_GIF" | cut -f1))"
    fi

    if [[ -f "$OUTPUT_GIF" ]]; then
        log "Default: $(basename "$OUTPUT_GIF") ($(du -h "$OUTPUT_GIF" | cut -f1))"
    fi

    echo
    echo "Add to README.md:"
    echo
    echo "  ![${DEMO_NAME} demo](${demo_path}/output/${DEMO_NAME}.gif)"
    if [[ -f "$SHOWCASE_GIF" ]]; then
        echo "  ![${DEMO_NAME} themes](${demo_path}/output/${DEMO_NAME}_showcase.gif)"
    fi
    echo
}

# ================================ Full Pipeline ==============================

run_full_pipeline() {
    # Run the complete demo generation pipeline
    # Usage: run_full_pipeline <python_module> [title] [rows] [cols]

    local python_module="$1"
    local title="${2:-hledger-preprocessor ${DEMO_NAME}}"
    local rows="${3:-$DEFAULT_ROWS}"
    local cols="${4:-$DEFAULT_COLS}"

    # 1. Record
    record_demo "$python_module" "$title" "$rows" "$cols" || exit 1

    # 2. Post-process
    postprocess_cast || exit 1

    # 3. Generate themed GIFs
    generate_themed_gifs || exit 1

    # 4. Create showcase
    create_showcase || true  # Don't fail if showcase fails

    # 5. Set default and optimize
    set_default_gif || exit 1
    optimize_gif || true

    # 6. Summary
    print_summary
}
