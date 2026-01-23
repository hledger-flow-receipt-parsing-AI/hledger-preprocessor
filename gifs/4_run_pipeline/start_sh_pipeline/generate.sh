#!/usr/bin/env bash
# =============================================================================
# Start.sh Pipeline Demo - GIF Generator
#
# Demonstrates the full hledger-preprocessor pipeline:
# 1. Preprocess assets
# 2. (Show generated files)
# =============================================================================

set -euo pipefail

# Source common utilities
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/../scripts/common.sh"

# Initialize demo (sets up paths, runs preflight checks)
init_demo "start_sh_pipeline" "$@"

# Run the full pipeline with the start_sh_demo module
run_full_pipeline \
    "gifs.automation.start_sh_demo" \
    "hledger-preprocessor: Full Pipeline" \
    40 \
    120

exit 0
