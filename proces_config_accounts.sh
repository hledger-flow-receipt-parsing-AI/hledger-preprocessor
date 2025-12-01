#!/bin/bash

# Reusable function to process any array of accounts from YAML
process_accounts() {
    local config_filepath="$1"
    local working_subdir="$2"
    local finance_dir="$3"
    local json_stream="$4"        # The JSON input (from yq)

    # read -p "0bank_or_asset=$bank_or_asset"
    echo "$json_stream" | jq -c '.[]' | while IFS= read -r account; do
        echo "account=$account"
        local input_csv_filename base_currency account_holder bank_or_wallet account_type

        input_csv_filename=$(echo "$account" | jq -r '.input_csv_filename // empty')
        base_currency=$(echo "$account" | jq -r '.base_currency // empty')
        account_holder=$(echo "$account" | jq -r '.account_holder // empty')
        bank_or_wallet=$(echo "$account" | jq -r '.bank // empty')
        account_type=$(echo "$account" | jq -r '.account_type // empty')

        # Skip if no CSV filename
        if [[ -z "$input_csv_filename" || "$input_csv_filename" == "null" || "$input_csv_filename" == "None" || "$input_csv_filename" == "nil" || ! "$input_csv_filename" =~ \.csv$ ]]; then
            echo "Info: No valid CSV file specified for (account_holder=$account_holder: bank_or_wallet=$bank_or_wallet, account_type=$account_type). Skipping."
            continue

            # TODO: determine what you need to do here.
            # local csv_filepath="$finance_dir/$account_holder/$bank_or_wallet/$account_type/$base_currency.csv"
            # echo "csv_filepath=$csv_filepath"

        else
            local csv_filepath="$finance_dir/$input_csv_filename"
        fi

        # Verify CSV file exists
        if [[ ! -f "$csv_filepath" ]]; then
            echo "CSV file '$csv_filepath' not found in '$finance_dir'."
            echo "   PWD=$PWD"
            continue
        fi

        echo "Processing: $csv_filepath"
        echo "   ACCOUNT_HOLDER=$account_holder, BANK_OR_WALLET=$bank_or_wallet, ACCOUNT_TYPE=$account_type"
        echo "   BASE_CURRENCY=$base_currency, WORKING_SUBDIR=$working_subdir"
        echo ""

        # Run preprocessor
        if ! hledger_preprocessor --config "$config_filepath" --new-setup; then
            echo "Error: hledger_preprocessor --new-setup failed for '$csv_filepath'."
            exit 1
        fi

        echo "PWD=$PWD"
        echo "PREPROCESS_COMMAND=hledger_preprocessor --config $config_filepath --new-setup"
        echo ""
    done
}

complete_asset_prerequisites() {
    local config_filepath="$1"

    hledger_preprocessor \
        --config "$config_filepath" \
        --link-receipts-to-transactions || {
        echo "Error: hledger_preprocessor --link-receipts-to-transactions failed."
        exit 1
    }

}

# Main function to handle both banks and assets
proces_config_accounts() {
    local config_filepath="$1"
    local working_subdir="$2"
    local finance_dir="$3"

    check_yaml_prerequisites "$config_filepath" "$working_subdir"

    # === Process .account_configs (banks) ===
    if yq e '.account_configs' "$config_filepath" >/dev/null 2>&1 && [ "$(yq e '.account_configs | length' "$config_filepath")" -gt 0 ]; then
        echo "Found accounts. Processing bank accounts..."
        local bank_json
        bank_json=$(yq e -o=json '.account_configs' "$config_filepath")
        process_accounts "$config_filepath" "$working_subdir" "$finance_dir" "$bank_json"
    else
        echo "No 'accounts' found or empty in '$config_filepath'. Skipping bank processing."
    fi

    # === Process .asset_accounts ===
    complete_asset_prerequisites "$config_filepath"
}
