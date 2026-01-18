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
init_demo "03_label_receipt" "$@"

# Run the full pipeline with the simulated label demo (avoids X11/TUI issues)
run_full_pipeline \
    "gifs.automation.simulated_label_demo" \
    "Step 3: Label Your Receipt" \
    35 \
    60

exit 0
