#!/bin/bash

check_yaml_prerequisites() {
    local config_filepath="$1"
    local working_subdir="$2"
    # local general_config_filepath="$3"

    # Ensure yq and jq are installed
    if ! command -v yq &> /dev/null; then
        echo "Error: yq is required to parse YAML. Install mikefarah/yq (version 4.x): https://github.com/mikefarah/yq"
        exit 1
    fi
    if ! command -v jq &> /dev/null; then
        echo "Error: jq is required to parse JSON. Install jq: https://jqlang.github.io/jq/"
        exit 1
    fi

    # Check yq version compatibility
    yq_version=$(yq --version 2>&1)
    if ! echo "$yq_version" | grep -q "mikefarah"; then
        echo "Error: Incompatible yq version detected. Requires mikefarah/yq (version 4.x)."
        echo "Current yq version: $yq_version"
        echo "Install SNAP mikefarah/yq: https://github.com/mikefarah/yq"
        exit 1
    fi

    # Check if file exists
    if [[ ! -f "$config_filepath" ]]; then
        echo "Error: Config file '$config_filepath' not found."
        exit 1
    fi

    # Check if file is a YAML file
    if [[ "$config_filepath" != *.yaml && "$config_filepath" != *.yml ]]; then
        echo "Error: Config file '$config_filepath' is not a YAML file (.yaml or .yml expected)."
        exit 1
    fi

    # Check if working directory exists
    if [[ ! -d "$working_subdir" ]]; then
        echo "Error: Working directory '$working_subdir' not found."
        exit 1
    fi
}
