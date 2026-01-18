#!/usr/bin/env bash
# =============================================================================
# Match Receipt to CSV Demo - GIF Generator
#
# Demonstrates automatic linking of receipts to bank CSV transactions
# =============================================================================

set -euo pipefail

# Source common utilities
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/../scripts/common.sh"

# Initialize demo (sets up paths, runs preflight checks)
init_demo "04_match_receipt_to_csv" "$@"

# Run the full pipeline with the simulated match demo
# Note: Uses simulated output because the real command requires actual
# data directories. The simulation shows realistic matching output.
run_full_pipeline \
    "gifs.automation.simulated_match_demo" \
    "Step 4: Match Receipt to Transaction" \
    38 \
    100

exit 0
