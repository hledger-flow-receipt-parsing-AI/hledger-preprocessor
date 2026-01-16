#!/usr/bin/env bash
# =============================================================================
# hledger-preprocessor Demo Recorder → GIF Generator
# Creates a clean asciinema recording and converts it to optimized GIFs
# with multiple color themes, then combines them into a showcase
# =============================================================================

set -euo pipefail

# ------------------------- Configuration Variables ---------------------------
CONFIG_FILEPATH="${1:?Error: Missing config file path argument.}"
export CONFIG_FILEPATH

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

OUTPUT_CAST="${SCRIPT_DIR}/demo.cast"
OUTPUT_GIF="${SCRIPT_DIR}/demo.gif"

# ----------------------------- Colors ---------------------------------------
RED="$(tput setaf 1)"
GREEN="$(tput setaf 2)"
PURPLE="$(tput setaf 5)"
ORANGE="$(tput setaf 3)"
BOLD="$(tput bold)"
RESET="$(tput sgr0)"

# ------------------------- Recording Settings --------------------------------
RECORDER_TITLE="hledger-preprocessor receipt matcher"
ROWS=40
COLS=120
IDLE_TIME_LIMIT=2
FONT_SIZE=20

# ------------------------- Theme Definitions ---------------------------------
# Format: "name:theme_value"
# Built-in themes: asciinema, dracula, monokai, solarized-dark, solarized-light
# Custom themes: comma-separated hex colors (bg,fg,black,red,green,yellow,blue,magenta,cyan,white)
declare -a THEMES=(
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

# ----------------------------- Functions ------------------------------------
log()    { echo -e "${BOLD}${GREEN}[+]${RESET} $*" ; }
warn()   { echo -e "${BOLD}${ORANGE}[!]${RESET} $*" ; }
error()  { echo -e "${BOLD}${RED}[✗]${RESET} $*" ; }
header() { echo -e "${PURPLE}${BOLD}=== $1 ===${RESET}" ; }

# ----------------------------- Pre-flight Checks ----------------------------
header "hledger-preprocessor Demo Recorder"

# Check we're in the right conda environment
if [[ "$(python -c 'import sys; print(sys.executable)' 2>/dev/null || echo '')" != */hledger_preprocessor/* ]]; then
    error "Not in the 'hledger_preprocessor' conda environment!"
    warn "Please run: conda activate hledger_preprocessor"
    exit 1
fi

# Check gifsicle is available (required for combining themes)
if ! command -v gifsicle >/dev/null 2>&1; then
    error "gifsicle not found!"
    warn "Install with: sudo apt install gifsicle"
    exit 1
fi

log "Using config: ${CONFIG_FILEPATH}"

# Remove old files
rm -f "$OUTPUT_CAST" "$OUTPUT_GIF" "${SCRIPT_DIR}"/demo_*.gif

# ----------------------------- Recording ------------------------------------
header "Starting asciinema recording..."

# Run the Python automation module via asciinema
if asciinema rec "$OUTPUT_CAST" \
    --command="python -m gifs.automation.receipt_editor" \
    --title "$RECORDER_TITLE" \
    --idle-time-limit="$IDLE_TIME_LIMIT" \
    --rows "$ROWS" \
    --cols "$COLS" \
    --env="CONFIG_FILEPATH,PYTHONPATH" \
    -y -q; then
    log "Recording completed successfully → ${OUTPUT_CAST}"
else
    error "asciinema recording failed!"
    exit 1
fi

# ----------------------------- Post-process cast file ------------------------
log "Post-processing cast file..."
CAST_FILE="$OUTPUT_CAST" python -m gifs.automation.cast_postprocess

# ----------------------------- GIF Conversion -------------------------------
header "Converting to GIFs using agg (${#THEMES[@]} themes)..."

# Ensure agg is available
if ! python -c "import agg" &>/dev/null; then
    log "Installing agg (asciinema → GIF converter)..."
    pip install -q agg || { error "Failed to install agg"; exit 1; }
fi

# Array to store generated GIF paths
declare -a GENERATED_GIFS=()

# Generate a GIF for each theme
for theme_entry in "${THEMES[@]}"; do
    # Parse theme name and value
    theme_name="${theme_entry%%:*}"
    theme_value="${theme_entry#*:}"

    output_file="${SCRIPT_DIR}/demo_${theme_name}.gif"

    log "Generating ${theme_name} theme..."

    if asciinema-agg "$OUTPUT_CAST" "$output_file" \
        --theme "$theme_value" \
        --font-size "$FONT_SIZE" \
        --renderer resvg \
        --line-height 1.2; then
        log "  → ${output_file}"
        GENERATED_GIFS+=("$output_file")
    else
        warn "  Failed to generate ${theme_name} theme, skipping..."
    fi
done

echo
log "Generated ${#GENERATED_GIFS[@]} theme variants"

# ----------------------------- Combine into Showcase -------------------------
header "Creating combined theme showcase..."

# Combine all GIFs into one showcase (each theme plays once, then loops)
SHOWCASE_GIF="${SCRIPT_DIR}/demo_showcase.gif"
log "Combining all themes into showcase..."

# Use gifsicle to concatenate GIFs
gifsicle --merge "${GENERATED_GIFS[@]}" -o "$SHOWCASE_GIF"

log "Showcase GIF created: ${BOLD}${SHOWCASE_GIF}${RESET}"
log "Showcase size: $(du -h "$SHOWCASE_GIF" | cut -f1)"

# Also copy the first theme as the default demo.gif
cp "${GENERATED_GIFS[0]}" "$OUTPUT_GIF"
log "Default demo.gif set to: $(basename "${GENERATED_GIFS[0]}")"

echo
header "Summary"
echo
log "Individual theme GIFs:"
for gif in "${GENERATED_GIFS[@]}"; do
    echo "   - $(basename "$gif") ($(du -h "$gif" | cut -f1))"
done
echo
if [[ -f "${SCRIPT_DIR}/demo_showcase.gif" ]]; then
    log "Showcase (all themes): demo_showcase.gif ($(du -h "${SCRIPT_DIR}/demo_showcase.gif" | cut -f1))"
fi
log "Default: demo.gif"
echo
echo "   Add to your README.md:"
echo
echo "   ![hledger-preprocessor demo](gifs/demo.gif)"
echo "   ![hledger-preprocessor themes](gifs/demo_showcase.gif)"
echo

# Optimize with gifsicle (lossless only for crisp text)
log "Optimizing GIF with gifsicle (lossless)..."
gifsicle -O3 -o "${OUTPUT_GIF}.tmp" "$OUTPUT_GIF" && mv "${OUTPUT_GIF}.tmp" "$OUTPUT_GIF"
log "Optimized! Size: $(du -h "$OUTPUT_GIF" | cut -f1)"

exit 0
