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

# Run the full pipeline with the match receipt module
run_full_pipeline \
    "gifs.automation.match_receipt_demo" \
    "Step 4: Match Receipt to Transaction" \
    35 \
    90

exit 0
