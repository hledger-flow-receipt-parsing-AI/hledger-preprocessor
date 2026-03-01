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

# Run the full pipeline with the full-path receipt labelling demo
# (shows config → categories → TUI receipt editing)
run_full_pipeline \
    "gifs.automation.real_label_simple_receipt_demo" \
    "US-2b.1: Label a Simple Receipt (Full Path)" \
    50 \
    120

exit 0
