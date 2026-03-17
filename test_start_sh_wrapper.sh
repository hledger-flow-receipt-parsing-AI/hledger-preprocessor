#!/bin/bash
set -e

# Source the helper scripts
source process_yaml_prerequisites.sh

# Use test environment variables (already set in env)
export RANDOMIZE_DATA="$RANDOMIZE_DATA"
export FINANCE_DIR="$FINANCE_DIR"
export WORKING_DIR="$WORKING_DIR"
export START_JOURNAL_FILEPATH="$START_JOURNAL_FILEPATH"
export RECEIPT_IMAGES_DIR="$RECEIPT_IMAGES_DIR"
export RECEIPT_LABELS_DIR="$RECEIPT_LABELS_DIR"
export GENERAL_CONFIG_FILEPATH="$GENERAL_CONFIG_FILEPATH"
export ABS_ASSET_PATH="$ABS_ASSET_PATH"
export ASSET_TRANSACTION_CSVS="$ASSET_TRANSACTION_CSVS"

# Simplified validate_config that skips the interactive TUI parts
validate_config() {
    if [ ! -f "$GENERAL_CONFIG_FILEPATH" ]; then
        echo "Error: Config file $GENERAL_CONFIG_FILEPATH does not exist."
        exit 1
    fi

    # Just check prerequisites, skip process_accounts which calls interactive TUI
    check_yaml_prerequisites "$GENERAL_CONFIG_FILEPATH" "$WORKING_DIR"
}

# Function to initialize and activate conda environment
activate_conda() {
    if ! command -v conda &> /dev/null; then
        echo "Error: conda command not found."
        exit 1
    fi

    source "$(conda info --base)/etc/profile.d/conda.sh" 2>/dev/null || {
        echo "Error: Failed to initialize conda."
        exit 1
    }

    conda activate hledger_preprocessor || {
        echo "Error: Failed to activate conda environment."
        exit 1
    }
}

# Print config for debugging
echo "WORKING_DIR=$WORKING_DIR"
echo "START_JOURNAL_FILEPATH=$START_JOURNAL_FILEPATH"
echo "GENERAL_CONFIG_FILEPATH=$GENERAL_CONFIG_FILEPATH"

# Start with empty working dir - BUT keep/recreate import structure
rm -rf "$WORKING_DIR"
mkdir -p "$WORKING_DIR"

# Recreate the hledger-flow import directory structure
# Only for accounts in the simplified config: triodos bank + EUR wallet
mkdir -p "$WORKING_DIR/import/at/triodos/checking/1-in"
mkdir -p "$WORKING_DIR/import/at/triodos/checking/2-csv"
mkdir -p "$WORKING_DIR/import/at/triodos/checking/3-journal"
mkdir -p "$WORKING_DIR/import/at/wallet/physical/1-in"
mkdir -p "$WORKING_DIR/import/at/wallet/physical/2-csv"
mkdir -p "$WORKING_DIR/import/at/wallet/physical/3-journal"

# Create basic rules files for hledger-flow
cat > "$WORKING_DIR/import/at/triodos/checking/triodos.rules" << 'RULES'
# hledger CSV import rules for triodos
skip 0
fields date, _, amount, _, payee, _, _, description, _
date-format %d-%m-%Y
currency EUR
account1 Assets:Checking:Triodos
RULES

cat > "$WORKING_DIR/import/at/wallet/physical/eur.rules" << 'RULES'
skip 0
fields date, amount, description
date-format %Y-%m-%d
currency EUR
account1 Assets:Wallet:Physical:EUR
RULES

# Initialize and activate conda first (needed for yq check)
activate_conda

# Validate config
validate_config

echo "NEXT PREPROCESS ASSETS COMMAND."
echo ""

# Preprocess accounts without csvs (EUR wallet from receipts)
hledger_preprocessor \
    --config "$GENERAL_CONFIG_FILEPATH" \
    --preprocess-assets || {
    echo "Error: hledger_preprocessor --preprocess-assets failed."
    exit 1
}

# Copy config.yaml to locations where preprocess/createRules scripts expect it
# These scripts use "../config.yaml" relative to their account type directory
# So for import/at/wallet/physical/, it needs import/at/wallet/config.yaml
mkdir -p "$WORKING_DIR/import/at/wallet"
cp "$GENERAL_CONFIG_FILEPATH" "$WORKING_DIR/import/at/wallet/config.yaml"
mkdir -p "$WORKING_DIR/import/at/triodos"
cp "$GENERAL_CONFIG_FILEPATH" "$WORKING_DIR/import/at/triodos/config.yaml"

echo "Running hledger-flow import."
echo ""

# Run hledger-flow to import/process CSVs
cd "$WORKING_DIR"
hledger-flow import || {
    echo "Error: hledger-flow import failed."
    exit 1
}

# Add starting position to all-years.journal if not already included
grep -q "include $START_JOURNAL_FILEPATH" "$WORKING_DIR/all-years.journal" 2>/dev/null || \
    echo "include $START_JOURNAL_FILEPATH" >> "$WORKING_DIR/all-years.journal"

# Generate balance report (skip Dash app via SKIP_DASH)
hledger bal -X EUR -f "$WORKING_DIR/all-years.journal" || {
    echo "Error: hledger balance report failed."
    exit 1
}

hledger_plot --config "$GENERAL_CONFIG_FILEPATH" --journal-filepath "$WORKING_DIR/all-years.journal" -d EUR -es || {
    echo "Error: hledger_plot failed."
    exit 1
}

echo "start.sh completed successfully!"
