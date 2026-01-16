#!/usr/bin/env bash
# =============================================================================
# Edit Receipt Demo - GIF Generator
#
# Demonstrates editing a receipt's category using the TUI interface.
# =============================================================================

set -euo pipefail

# Source common utilities
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/../scripts/common.sh"

# Initialize demo (sets up paths, runs preflight checks)
init_demo "edit_receipt" "$@"

# Run the full pipeline with the receipt editor module
run_full_pipeline \
    "gifs.automation.receipt_editor" \
    "hledger-preprocessor: Edit Receipt" \
    40 \
    120

exit 0
