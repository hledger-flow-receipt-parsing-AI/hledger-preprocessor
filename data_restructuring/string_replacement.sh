#!/bin/bash

# Script to rename "amount_out_account" to "tendered_amount_out"
# in all *.json files under a user-provided directory.
# Always creates .bak backups.
# Lists found files and asks for confirmation before proceeding.

# Exit on any error
set -e

# Check if directory argument is provided
if [ $# -ne 1 ]; then
    echo "Usage: $0 <target-directory>"
    exit 1
fi

TARGET_DIR="$1"

# Verify directory exists
if [ ! -d "$TARGET_DIR" ]; then
    echo "Error: Directory '$TARGET_DIR' does not exist."
    exit 1
fi

# Find all *.json files recursively and store in array
mapfile -t JSON_FILES < <(find "$TARGET_DIR" -type f -name '*.json' | sort)

# If no files found, exit early
if [ ${#JSON_FILES[@]} -eq 0 ]; then
    echo "No *.json files found in '$TARGET_DIR' or its subdirectories."
    exit 0
fi

# Print the list of found files
echo "Found ${#JSON_FILES[@]} JSON file(s):"
printf '  %s\n' "${JSON_FILES[@]}"
echo

# Ask for confirmation
read -rp "Proceed with replacement (creates .bak backups)? [y/N] " answer
echo

# Default to no if empty or not y/Y
if [[ ! "$answer" =~ ^[yY]$ ]]; then
    echo "Operation cancelled."
    exit 0
fi

# Perform the replacement with backups
echo "Replacing 'amount_out_account' with 'tendered_amount_out'..."
find "$TARGET_DIR" -type f -name '*.json' \
    -exec sed -i.bak 's/amount_out_account/tendered_amount_out/g' {} +

echo "Replacement complete."
echo "Backups created with .bak extension (e.g., file.json.bak)."
