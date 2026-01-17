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

# Run the full pipeline with the add category module
run_full_pipeline \
    "gifs.automation.add_category_demo" \
    "Step 2: Define Categories" \
    25 \
    80

exit 0
