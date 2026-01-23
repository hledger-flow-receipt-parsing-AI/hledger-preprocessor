#!/usr/bin/env bash
# =============================================================================
# Run Pipeline Demo - GIF Generator
#
# Demonstrates the full hledger-preprocessor pipeline (./start.sh):
# 1. Preprocess assets (receipts → CSVs)
# 2. hledger-flow import (CSVs → journals)
# 3. hledger_plot (journals → SVG plots)
#
# Step 5 of the 5-GIF demo sequence.
# =============================================================================

set -euo pipefail

# Source common utilities
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/../scripts/common.sh"

# Initialize demo (sets up paths, runs preflight checks)
init_demo "05_run_pipeline" "$@"

# Run the full pipeline with the start_sh_demo module
run_full_pipeline \
    "gifs.automation.start_sh_demo" \
    "Step 5: Run the Pipeline" \
    40 \
    120

exit 0
