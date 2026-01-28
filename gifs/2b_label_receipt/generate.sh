#!/usr/bin/env bash
# =============================================================================
# Label Receipt Demo - GIF Generator
#
# Demonstrates labelling a receipt using the TUI interface.
# Step 3 of the 5-GIF demo sequence.
# =============================================================================

set -euo pipefail

# Source common utilities
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/../scripts/common.sh"

# Initialize demo (sets up paths, runs preflight checks)
init_demo "2b_label_receipt" "$@"

# Run the full pipeline with the real receipt editor TUI automation
run_full_pipeline \
    "gifs.automation.receipt_editor" \
    "Step 4: Label Your Receipt" \
    50 \
    120

exit 0
