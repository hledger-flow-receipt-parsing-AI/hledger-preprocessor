#!/usr/bin/env bash
# =============================================================================
# Common utilities for GIF generation scripts
# Source this file from individual demo scripts
# =============================================================================

set -euo pipefail

# ----------------------------- Colors -----------------------------------------
RED="$(tput setaf 1)"
GREEN="$(tput setaf 2)"
YELLOW="$(tput setaf 3)"
BLUE="$(tput setaf 4)"
PURPLE="$(tput setaf 5)"
CYAN="$(tput setaf 6)"
ORANGE="$(tput setaf 3)"  # Fallback, not all terminals have orange
BOLD="$(tput bold)"
RESET="$(tput sgr0)"

# ----------------------------- Logging Functions ------------------------------
log()    { echo -e "${BOLD}${GREEN}[+]${RESET} $*" ; }
warn()   { echo -e "${BOLD}${ORANGE}[!]${RESET} $*" ; }
error()  { echo -e "${BOLD}${RED}[✗]${RESET} $*" ; }
header() { echo -e "${PURPLE}${BOLD}=== $1 ===${RESET}" ; }

# ----------------------------- Pre-flight Checks ------------------------------
check_conda_env() {
    local expected_env="${1:-hledger_preprocessor}"
    if [[ "$(python -c 'import sys; print(sys.executable)' 2>/dev/null || echo '')" != */"${expected_env}"/* ]]; then
        error "Not in the '${expected_env}' conda environment!"
        warn "Please run: conda activate ${expected_env}"
        exit 1
    fi
}

check_gifsicle() {
    if ! command -v gifsicle >/dev/null 2>&1; then
        error "gifsicle not found!"
        warn "Install with: sudo apt install gifsicle"
        exit 1
    fi
}

check_asciinema() {
    if ! command -v asciinema >/dev/null 2>&1; then
        error "asciinema not found!"
        warn "Install with: pip install asciinema"
        exit 1
    fi
}

check_agg() {
    if ! command -v asciinema-agg >/dev/null 2>&1; then
        log "Installing agg (asciinema → GIF converter)..."
        pip install -q agg || { error "Failed to install agg"; exit 1; }
    fi
}

# ----------------------------- Theme Definitions ------------------------------
# Format: "name:theme_value"
# Built-in themes: asciinema, dracula, monokai, solarized-dark, solarized-light
# Custom themes: comma-separated hex colors (bg,fg,black,red,green,yellow,blue,magenta,cyan,white)
declare -a DEFAULT_THEMES=(
    # Built-in themes
    "dracula:dracula"
    "monokai:monokai"
    "solarized-dark:solarized-dark"
    "solarized-light:solarized-light"
    # Custom retro themes
    "amber:0a0a0a,ffb000,1a1a1a,cc4400,ff8800,ffb000,ff6600,cc6600,ffcc00,ffdd88"
    "green-phosphor:0a0a0a,33ff33,1a1a1a,00cc00,33ff33,66ff66,00aa00,009900,99ff99,ccffcc"
    "cyan-cool:0a0f14,00ffff,0a1a1f,ff6666,66ffcc,ffff66,6699ff,ff66ff,00ffff,ffffff"
    "matrix:000000,00ff00,0a0a0a,ff0000,00ff00,ffff00,0066ff,ff00ff,00ffff,ffffff"
)

# ----------------------------- Recording Settings -----------------------------
DEFAULT_ROWS=50
DEFAULT_COLS=120
DEFAULT_IDLE_TIME_LIMIT=2
DEFAULT_FONT_SIZE=20

# ----------------------------- GIF Generation ---------------------------------
generate_themed_gifs() {
    # Usage: generate_themed_gifs CAST_FILE OUTPUT_DIR [FONT_SIZE]
    local cast_file="$1"
    local output_dir="$2"
    local font_size="${3:-$DEFAULT_FONT_SIZE}"
    local themes=("${DEFAULT_THEMES[@]}")

    check_agg

    local -a generated_gifs=()

    for theme_entry in "${themes[@]}"; do
        local theme_name="${theme_entry%%:*}"
        local theme_value="${theme_entry#*:}"
        local output_file="${output_dir}/demo_${theme_name}.gif"

        log "Generating ${theme_name} theme..."

        if asciinema-agg "$cast_file" "$output_file" \
            --theme "$theme_value" \
            --font-size "$font_size" \
            --renderer resvg \
            --line-height 1.2; then
            log "  → ${output_file}"
            generated_gifs+=("$output_file")
        else
            warn "  Failed to generate ${theme_name} theme, skipping..."
        fi
    done

    echo
    log "Generated ${#generated_gifs[@]} theme variants"

    # Return the list via a global variable
    GENERATED_GIFS=("${generated_gifs[@]}")
}

create_showcase_gif() {
    # Usage: create_showcase_gif OUTPUT_DIR
    local output_dir="$1"
    local showcase_gif="${output_dir}/demo_showcase.gif"

    if [[ ${#GENERATED_GIFS[@]} -eq 0 ]]; then
        warn "No GIFs to combine into showcase"
        return 1
    fi

    header "Creating combined theme showcase..."
    log "Combining all themes into showcase..."

    gifsicle --merge "${GENERATED_GIFS[@]}" -o "$showcase_gif"

    log "Showcase GIF created: ${BOLD}${showcase_gif}${RESET}"
    log "Showcase size: $(du -h "$showcase_gif" | cut -f1)"

    # Set the first theme as the default demo.gif
    local default_gif="${output_dir}/demo.gif"
    cp "${GENERATED_GIFS[0]}" "$default_gif"
    log "Default demo.gif set to: $(basename "${GENERATED_GIFS[0]}")"

    # Optimize with gifsicle (lossless only for crisp text)
    log "Optimizing default GIF with gifsicle (lossless)..."
    gifsicle -O3 -o "${default_gif}.tmp" "$default_gif" && mv "${default_gif}.tmp" "$default_gif"
    log "Optimized! Size: $(du -h "$default_gif" | cut -f1)"
}

print_summary() {
    # Usage: print_summary OUTPUT_DIR
    local output_dir="$1"

    echo
    header "Summary"
    echo
    log "Individual theme GIFs:"
    for gif in "${GENERATED_GIFS[@]}"; do
        echo "   - $(basename "$gif") ($(du -h "$gif" | cut -f1))"
    done
    echo
    if [[ -f "${output_dir}/demo_showcase.gif" ]]; then
        log "Showcase (all themes): demo_showcase.gif ($(du -h "${output_dir}/demo_showcase.gif" | cut -f1))"
    fi
    log "Default: demo.gif"
    echo
    echo "   Add to your README.md:"
    echo
    echo "   ![hledger-preprocessor demo](gifs/demo.gif)"
    echo "   ![hledger-preprocessor themes](gifs/demo_showcase.gif)"
    echo
}

record_demo() {
    # Usage: record_demo CAST_FILE PYTHON_MODULE [TITLE] [ROWS] [COLS] [IDLE_TIME_LIMIT]
    local cast_file="$1"
    local python_module="$2"
    local title="${3:-hledger-preprocessor demo}"
    local rows="${4:-$DEFAULT_ROWS}"
    local cols="${5:-$DEFAULT_COLS}"
    local idle_time_limit="${6:-$DEFAULT_IDLE_TIME_LIMIT}"

    header "Starting asciinema recording..."

    if asciinema rec "$cast_file" \
        --command="python -m ${python_module}" \
        --title "$title" \
        --idle-time-limit="$idle_time_limit" \
        --rows "$rows" \
        --cols "$cols" \
        --env="CONFIG_FILEPATH,PYTHONPATH" \
        -y -q; then
        log "Recording completed successfully → ${cast_file}"
    else
        error "asciinema recording failed!"
        exit 1
    fi
}

postprocess_cast() {
    # Usage: postprocess_cast CAST_FILE
    local cast_file="$1"

    log "Post-processing cast file..."
    CAST_FILE="$cast_file" python -m gifs.automation.cast_postprocess
}
