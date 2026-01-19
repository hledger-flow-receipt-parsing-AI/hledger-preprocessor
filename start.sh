#!/bin/bash
source process_yaml_prerequisites.sh
source proces_config_accounts.sh


# Parse command line arguments
usage() {
    echo "Usage: $0 --config <path-to-config.yaml> [--randomize]"
    echo ""
    echo "Arguments:"
    echo "  --config <path>   Path to the config.yaml file (required)"
    echo "  --randomize       Enable data randomization (optional, default: false)"
    exit 1
}

RANDOMIZE_DATA="false"
GENERAL_CONFIG_FILEPATH=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --config)
            if [[ -z "$2" || "$2" == --* ]]; then
                echo "Error: --config requires a path argument."
                usage
            fi
            GENERAL_CONFIG_FILEPATH="$2"
            shift 2
            ;;
        --randomize)
            RANDOMIZE_DATA="true"
            shift
            ;;
        -h|--help)
            usage
            ;;
        *)
            echo "Error: Unknown argument: $1"
            usage
            ;;
    esac
done

# Validate config path was provided
if [[ -z "$GENERAL_CONFIG_FILEPATH" ]]; then
    echo "Error: --config argument is required."
    usage
fi

# Validate config file exists
if [[ ! -f "$GENERAL_CONFIG_FILEPATH" ]]; then
    echo "Error: Config file '$GENERAL_CONFIG_FILEPATH' does not exist."
    exit 1
fi

# Check yq is available before loading config
if ! command -v yq &> /dev/null; then
    echo "Error: yq is required to parse YAML. Install mikefarah/yq (version 4.x): https://github.com/mikefarah/yq"
    exit 1
fi

# Load configuration from config.yaml
export GENERAL_CONFIG_FILEPATH
export RANDOMIZE_DATA

# Load paths from config.yaml using yq
export FINANCE_DIR=$(yq e '.dir_paths.root_finance_path' "$GENERAL_CONFIG_FILEPATH")
WORKING_SUBDIR=$(yq e '.dir_paths.working_subdir' "$GENERAL_CONFIG_FILEPATH")
export WORKING_DIR="$FINANCE_DIR/$WORKING_SUBDIR"

START_JOURNAL_RELATIVE=$(yq e '.file_names.start_journal_filepath' "$GENERAL_CONFIG_FILEPATH")
export START_JOURNAL_FILEPATH="$FINANCE_DIR/$START_JOURNAL_RELATIVE"

RECEIPT_IMAGES_RELATIVE=$(yq e '.dir_paths.receipt_images_dir' "$GENERAL_CONFIG_FILEPATH")
export RECEIPT_IMAGES_DIR="$FINANCE_DIR/$RECEIPT_IMAGES_RELATIVE"

RECEIPT_LABELS_RELATIVE=$(yq e '.dir_paths.receipt_labels_dir' "$GENERAL_CONFIG_FILEPATH")
export RECEIPT_LABELS_DIR="$FINANCE_DIR/$RECEIPT_LABELS_RELATIVE"

ASSET_CSVS_RELATIVE=$(yq e '.dir_paths.asset_transaction_csvs_dir' "$GENERAL_CONFIG_FILEPATH")
export ASSET_TRANSACTION_CSVS="$WORKING_DIR/$ASSET_CSVS_RELATIVE"

export ABS_ASSET_PATH="$WORKING_DIR/import/assets"

# Validate that required paths were loaded
if [[ -z "$FINANCE_DIR" || "$FINANCE_DIR" == "null" ]]; then
    echo "Error: dir_paths.root_finance_path not found in config."
    exit 1
fi

if [[ -z "$WORKING_SUBDIR" || "$WORKING_SUBDIR" == "null" ]]; then
    echo "Error: dir_paths.working_subdir not found in config."
    exit 1
fi

# End of configuration loading.
validate_config() {
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
# echo "ASSET_TRANSACTION_CSVS=$ASSET_TRANSACTION_CSVS"



# Start with an empty working dir such that your flow stays reproducible.
# rm -rf "$ASSET_TRANSACTION_CSVS"
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
echo "NEXT PREPROCESS ASSETS COMMAND."
echo ""
echo ""

# Preprocess accounts without csvs.
hledger_preprocessor \
            --config "$GENERAL_CONFIG_FILEPATH" \
            --preprocess-assets || {
            echo "Error: hledger_preprocessor --preprocess-assets failed."
            exit 1
}

echo "Running hledger-flow import."
echo ""
echo ""


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
