#!/usr/bin/env bash
# =============================================================================
# Setup Config Demo - GIF Generator
#
# Demonstrates how to configure hledger-preprocessor with config.yaml
# =============================================================================

set -euo pipefail

# Source common utilities
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/../scripts/common.sh"

# Initialize demo (sets up paths, runs preflight checks)
init_demo "01_setup_config" "$@"

# Run the full pipeline with the REAL config demo (using nano)
run_full_pipeline \
    "gifs.automation.real_config_demo" \
    "Step 1: Configure Your Accounts" \
    40 \
    115

exit 0
