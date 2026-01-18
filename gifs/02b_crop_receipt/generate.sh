#!/usr/bin/env bash
# =============================================================================
# Crop Receipt Demo - GIF Generator
#
# Demonstrates how to crop receipt images before labeling
# =============================================================================

set -euo pipefail

# Source common utilities
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/../scripts/common.sh"

# Initialize demo (sets up paths, runs preflight checks)
init_demo "02b_crop_receipt" "$@"

# Run the full pipeline with the simulated crop demo
run_full_pipeline \
    "gifs.automation.simulated_crop_demo" \
    "Step 2b: Crop Receipt Images" \
    35 \
    75

exit 0
