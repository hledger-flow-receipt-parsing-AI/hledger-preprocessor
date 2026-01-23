#!/usr/bin/env bash
# =============================================================================
# Show Plots Demo - GIF Generator
#
# Demonstrates hledger_plot visualizations (Sankey + Treemap)
# Shows the interactive Dash dashboard with financial plots.
# =============================================================================

set -euo pipefail

# Source common utilities
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/../scripts/common.sh"

# Initialize demo (sets up paths, runs preflight checks)
init_demo "06_show_plots" "$@"

# Run the full pipeline with the show plots module
run_full_pipeline \
    "gifs.automation.show_plots_demo" \
    "Bonus: Visualize Your Finances" \
    40 \
    120

exit 0
