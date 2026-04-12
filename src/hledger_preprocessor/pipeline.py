"""Full preprocessing pipeline -- replaces start.sh.

Orchestrates the complete flow:
  1. Load and validate config
  2. Clean working directory
  3. Set up account directory structures
  4. Pre-flight checks (categorisation + matching)
  5. Match transactions (receipts + CSV-to-CSV)
  6. Preprocess assets
  7. Run hledger-flow import (subprocess)
  8. Append start journal include
  9. Generate balance report / plots (subprocess)
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from typing import Any, Dict, List

from typeguard import typechecked

from hledger_config.config.load_config import Config, load_config
from hledger_core.generics.enums import ClassifierType, LogicType
from hledger_core.TransactionObjects.Receipt import Receipt
from hledger_preprocessor.checks.check_categorisation import (
    check_categorisation,
)
from hledger_preprocessor.checks.check_matching import check_matching
from hledger_preprocessor.get_models import get_models
from hledger_preprocessor.management.main_manager import (
    manage_batch_match_receipts,
    manage_creating_new_setup,
    manage_match_csv_to_csv,
    manage_matching_manual_receipt_objs_to_account_transactions,
    manage_preprocessing_assets,
)
from hledger_receipt_processing.reading_history.load_receipts_from_dir import (
    load_receipts_from_dir,
)


@typechecked
def run_pipeline(
    *,
    config_path: str,
    randomize: bool = False,
    non_interactive: bool = False,
) -> None:
    """Run the full preprocessing pipeline."""
    # --- 1. Load config ---
    print(f"Loading config from: {config_path}")
    config: Config = load_config(
        config_path=config_path,
        pre_processed_output_dir=None,
    )

    working_dir: str = config.get_working_subdir_path(assert_exists=False)
    start_journal: str = config.file_names.start_journal_filepath

    print(f"WORKING_DIR={working_dir}")
    print(f"START_JOURNAL_FILEPATH={start_journal}")
    print(f"GENERAL_CONFIG_FILEPATH={config_path}")

    # --- 2. Clean working directory ---
    if os.path.exists(working_dir):
        shutil.rmtree(working_dir)
    os.makedirs(working_dir, exist_ok=True)

    # --- 3. Validate config: set up account directory structures ---
    # Equivalent to start.sh's validate_config() which calls:
    #   proces_config_accounts -> hledger_preprocessor --new-setup per account
    #   complete_asset_prerequisites -> --link-receipts-to-transactions
    labelled_receipts: List[Receipt] = load_receipts_from_dir(config=config)

    manage_creating_new_setup(
        config=config,
        labelled_receipts=labelled_receipts,
    )

    models: Dict[ClassifierType, Dict[LogicType, Any]] = get_models(
        quick_categorisation=True
    )

    # Link receipts to transactions (asset prerequisites).
    manage_matching_manual_receipt_objs_to_account_transactions(
        config=config,
        models=models,
        labelled_receipts=labelled_receipts,
    )

    # --- 4. Pre-flight checks ---
    print("Checking for uncategorised transactions...")
    errors = check_categorisation(
        config=config,
        models=models,
        labelled_receipts=labelled_receipts,
    )
    if errors:
        print("")
        print("=" * 60)
        print(f"  {len(errors)} uncategorised transaction(s) found")
        print("=" * 60)
        for err in errors:
            print(str(err))
        print("=" * 60)
        print("Fix the uncategorised transactions above, then re-run.")
        sys.exit(1)
    print("")

    print("Checking for unmatched transactions...")
    check_matching(
        config=config,
        labelled_receipts=labelled_receipts,
    )
    print("")

    # --- 5. Match transactions (non-fatal, matches start.sh behavior) ---
    print("Matching transactions (receipts + CSV-to-CSV)...")
    print("")
    try:
        labelled_receipts = manage_batch_match_receipts(
            config=config,
            labelled_receipts=labelled_receipts,
        )

        if non_interactive:
            print("Skipping CSV-to-CSV matching (--non-interactive).")
        else:
            manage_match_csv_to_csv(
                config=config,
                labelled_receipts=labelled_receipts,
            )
    except Exception as e:
        print(f"Warning: transaction matching encountered errors (non-fatal).")
    print("")

    # --- 6. Preprocess assets ---
    print("NEXT PREPROCESS ASSETS COMMAND.")
    print("")
    print("")
    try:
        manage_preprocessing_assets(
            config=config,
            models=models,
            labelled_receipts=labelled_receipts,
        )
    except Exception as e:
        error_msg = str(e)
        if "UNCATEGORISED TRANSACTION" in error_msg:
            print("")
            print("=" * 60)
            print("  hledger-preprocessor found an uncategorised transaction.")
            print("=" * 60)
            print(error_msg)
            print("")
            sys.exit(1)
        else:
            print("Error: hledger_preprocessor --preprocess-assets failed.")
            print(error_msg)
            sys.exit(1)

    # --- 7. Run hledger-flow import ---
    print("Running hledger-flow import.")
    print("")
    result = subprocess.run(
        ["hledger-flow", "import"],
        cwd=working_dir,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        output = result.stdout + result.stderr
        if "UNCATEGORISED TRANSACTION" in output:
            print("")
            print("=" * 60)
            print("  hledger-flow import triggered an uncategorised transaction")
            print("  error in the hledger-preprocessor preprocessing step.")
            print("=" * 60)
            # Print relevant section
            for line in output.splitlines():
                if "UNCATEGORISED TRANSACTION" in line or "run" in line.lower():
                    print(line)
            print("")
            sys.exit(1)
        else:
            print("Error: hledger-flow import failed.")
            print(output)
            sys.exit(1)

    # --- 8. Append start journal include ---
    all_years_journal = os.path.join(working_dir, "all-years.journal")
    include_line = f"include {start_journal}"
    if os.path.exists(all_years_journal):
        with open(all_years_journal, "r") as f:
            content = f.read()
        if include_line not in content:
            with open(all_years_journal, "a") as f:
                f.write(f"{include_line}\n")

    # --- 9. Generate balance report / plots ---
    if randomize:
        result = subprocess.run(
            [
                "hledger_plot",
                "--config", config_path,
                "--journal-filepath", all_years_journal,
                "-d", "EUR",
                "-s",
                "-r",
            ],
        )
        if result.returncode != 0:
            print("Error: hledger_plot failed.")
            sys.exit(1)
    else:
        # Generate balance report
        result = subprocess.run(
            [
                "hledger", "bal",
                "-X", "EUR",
                "-f", all_years_journal,
            ],
        )
        if result.returncode != 0:
            print("Error: hledger balance report failed.")
            sys.exit(1)

        result = subprocess.run(
            [
                "hledger_plot",
                "--config", config_path,
                "--journal-filepath", all_years_journal,
                "-d", "EUR",
                "-s",
            ],
        )
        if result.returncode != 0:
            print("Error: hledger_plot failed.")
            sys.exit(1)
