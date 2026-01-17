#!/usr/bin/env bash
# =============================================================================
# Add Category Demo - GIF Generator
#
# Demonstrates how to add spending categories to categories.yaml
# =============================================================================

set -euo pipefail

# Source common utilities
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/../scripts/common.sh"

# Initialize demo (sets up paths, runs preflight checks)
init_demo "02_add_category" "$@"

# Run the full pipeline with the REAL categories demo (using nano)
run_full_pipeline \
    "gifs.automation.real_categories_demo" \
    "Step 2: Define Categories" \
    38 \
    95

exit 0
