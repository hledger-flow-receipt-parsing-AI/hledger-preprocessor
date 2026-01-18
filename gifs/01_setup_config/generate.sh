#!/usr/bin/env bash
# =============================================================================
# Setup Config Demo - GIF Generator
#
# Demonstrates how to configure hledger-preprocessor with config.yaml
# Uses yaml_typing_gif.py to render actual YAML file with typing animation
# =============================================================================

set -euo pipefail

# ================================ Config =====================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
DEMO_NAME="01_setup_config"
OUTPUT_DIR="${SCRIPT_DIR}/output"

# Input YAML file - use the test fixture
INPUT_YAML="${PROJECT_ROOT}/test/fixtures/config_templates/1_bank_1_wallet.yaml"
OUTPUT_GIF="${OUTPUT_DIR}/${DEMO_NAME}.gif"

# ================================ Colors =====================================
GREEN="$(tput setaf 2 2>/dev/null || echo '')"
BOLD="$(tput bold 2>/dev/null || echo '')"
RESET="$(tput sgr0 2>/dev/null || echo '')"

log() { echo -e "${BOLD}${GREEN}[+]${RESET} $*"; }

# ================================ Main =======================================

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Check input file exists
if [[ ! -f "$INPUT_YAML" ]]; then
    echo "Error: Input YAML not found: $INPUT_YAML"
    exit 1
fi

log "Generating config.yaml typing animation..."
log "  Input: $INPUT_YAML"
log "  Output: $OUTPUT_GIF"

# Ensure PYTHONPATH includes project root
export PYTHONPATH="${PROJECT_ROOT}:${PYTHONPATH:-}"

# Generate the GIF using yaml_typing_gif.py
python -m gifs.automation.yaml_typing_gif \
    --input "$INPUT_YAML" \
    --output "$OUTPUT_GIF" \
    --title "config.yaml" \
    --rows 35 \
    --cols 85

log "Done! GIF created at: $OUTPUT_GIF"

exit 0
