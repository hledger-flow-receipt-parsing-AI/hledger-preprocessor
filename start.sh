#!/bin/bash
source process_yaml_prerequisites.sh
source proces_config_accounts.sh


# Change this configuration to match your own setup.
export RANDOMIZE_DATA="false"  # Set to "true" or "false" as needed
export FINANCE_DIR="/home/$(whoami)/finance"
export WORKING_DIR="$FINANCE_DIR/finance_v8"
export START_JOURNAL_FILEPATH="$FINANCE_DIR/start_pos/2024_complete.journal"
export RECEIPT_IMAGES_DIR="$FINANCE_DIR/receipt_images"
export RECEIPT_LABELS_DIR="$FINANCE_DIR/receipt_labels"
export GENERAL_CONFIG_FILEPATH="$FINANCE_DIR/config.yaml"
export ABS_ASSET_PATH="$WORKING_DIR/import/assets"

# End of configuration.
validate_config() {
    if [ ! -f "$GENERAL_CONFIG_FILEPATH" ]; then
        echo "Error: Config file $GENERAL_CONFIG_FILEPATH does not exist."
        exit 1
    fi

    check_yaml_prerequisites "$GENERAL_CONFIG_FILEPATH" "$WORKING_DIR"
    proces_config_accounts "$GENERAL_CONFIG_FILEPATH" "$WORKING_DIR" "$FINANCE_DIR"
}

# Function to initialize and activate conda environment
activate_conda() {
    # Check if conda is installed
    if ! command -v conda &> /dev/null; then
        echo "Error: conda command not found. Please ensure conda is installed."
        exit 1
    fi

    # Initialize conda for the script
    source "$(conda info --base)/etc/profile.d/conda.sh" 2>/dev/null || {
        echo "Error: Failed to initialize conda. Run 'conda init' and restart your shell."
        exit 1
    }

    # Activate conda environment
    conda activate hledger_preprocessor || {
        echo "Error: Failed to activate conda environment 'hledger_preprocessor'."
        exit 1
    }
}


# Assert RANDOMIZE_DATA is either "true" or "false"
if [ "$RANDOMIZE_DATA" != "true" ] && [ "$RANDOMIZE_DATA" != "false" ]; then
    echo "Error: RANDOMIZE_DATA must be set to 'true' or 'false'."
    exit 1
fi

# Enable exit on error
set -e

# Give the user some orientation.
clear
echo "WORKING_DIR=$WORKING_DIR"
echo "START_JOURNAL_FILEPATH=$START_JOURNAL_FILEPATH"
echo "GENERAL_CONFIG_FILEPATH=$GENERAL_CONFIG_FILEPATH"



# Start with an empty working dir such that your flow stays reproducible.
rm -rf "$WORKING_DIR"
mkdir -p "$WORKING_DIR"

# Validate config and CSVs
validate_config

# Initialize and activate conda
activate_conda


# Preprocess accounts with csvs.
# hledger_preprocessor \
#             --config "$GENERAL_CONFIG_FILEPATH" \
#             --preprocess-csvs || {
#             echo "Error: hledger_preprocessor --preprocess-csvs failed."
#             exit 1
# }


# Preprocess accounts without csvs.
hledger_preprocessor \
            --config "$GENERAL_CONFIG_FILEPATH" \
            --preprocess-assets || {
            echo "Error: hledger_preprocessor --preprocess-assets failed."
            exit 1
}

# Run hledger-flow to import/process CSVs

cd "$WORKING_DIR"
hledger-flow import || {
    echo "Error: hledger-flow import failed."
    exit 1
}

# Add starting position to all-years.journal if not already included
grep -q "include $START_JOURNAL_FILEPATH" "$WORKING_DIR/all-years.journal" || echo "include $START_JOURNAL_FILEPATH" >> "$WORKING_DIR/all-years.journal"


# Add assets directory to all-years.journal if not already included
# grep -q "include $ABS_ASSET_PATH" "$WORKING_DIR/all-
# TODO: add include assets to this line.



# Plot financial situation
if [ "$RANDOMIZE_DATA" = "true" ]; then
    hledger_plot --config "$GENERAL_CONFIG_FILEPATH" --journal-filepath "$WORKING_DIR/all-years.journal" -d EUR -s -r || {
    echo "Error: hledger_plot failed."
    exit 1
    }
else
    # Generate balance report
    hledger bal -X EUR -f "$WORKING_DIR/all-years.journal" || {
        echo "Error: hledger balance report failed."
        exit 1
    }

    hledger_plot --config "$GENERAL_CONFIG_FILEPATH" --journal-filepath "$WORKING_DIR/all-years.journal" -d EUR -s || {
    echo "Error: hledger_plot failed."
    exit 1
    }
fi
