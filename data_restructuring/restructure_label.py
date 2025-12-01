import copy
import json
import shutil
from pathlib import Path
from pprint import pprint
from typing import Any, Union


def is_legacy_account_block(obj: Any) -> bool:
    """Pure detection of the exact legacy account pattern"""
    if not isinstance(obj, dict):
        return False

    keys = obj.keys()
    return (
        # len(keys) == 5
        # obj.get("asset_type") == "asset"
        # and obj.get("asset_category") == "assets:cash"
        # and "Currency." in obj.get("asset_category")
        # obj.get("account_holder") is None
        # and obj.get("bank") is None
        # and obj.get("account_type") is None
        "asset_category"
        in set(keys)
        # and {
        #     "asset_type",
        #     "account_holder",
        #     "bank",
        #     "account_type",
        #     "asset_category",
        # }
        # == set(keys)
    )


def get_sibling_value(container: dict, key: str) -> Any:
    """
    Generic: Get a value from the same dict level (sibling).
    Asserts the key exists exactly once and is not null.
    """
    if not isinstance(container, dict):
        raise TypeError("get_sibling_value expects a dict as container")

    matches = [k for k in container.keys() if k == key]

    if len(matches) == 0:
        raise KeyError(f"Required sibling key '{key}' not found at this level")
    if len(matches) > 1:
        raise ValueError(f"Key '{key}' appears more than once at this level")

    value = container[key]
    if value is None:
        raise ValueError(f"Key '{key}' exists but value is null/None")

    return value


def replace_legacy_account(container: dict) -> dict:
    """
    Called only when we know `container` has an 'account' key.
    Replaces legacy account block using currency from the same level.
    """
    account_obj = container["account"]

    if not is_legacy_account_block(account_obj):
        return container  # not legacy → leave untouched

    # Forcefully get currency from same level
    currency = get_sibling_value(container, "currency")
    account_obj.pop("asset_category")
    account_obj.pop("asset_type")
    account_obj["base_currency"] = currency
    input(f"account_obj={account_obj}")
    return {
        **container,  # keep all other keys
        "account": account_obj,
    }


def deep_replace_account(obj: Any) -> Any:
    """
    Recursively walk JSON and replace legacy account blocks.
    Only acts when 'account' and 'currency' are siblings.
    """
    if isinstance(obj, dict):
        # Case 1: This dict has an 'account' key → check if we need to replace
        if "account" in obj:
            try:
                return replace_legacy_account(obj)
            except (KeyError, ValueError, TypeError):
                # If currency missing or invalid → do NOT replace, keep original
                pass  # fall through to normal recursion

        # Case 2: Normal recursion into children
        result = {}
        for k, v in obj.items():
            result[k] = deep_replace_account(v)
        return result

    elif isinstance(obj, list):
        return [deep_replace_account(item) for item in obj]

    return obj  # primitive


# ——————————————————— MAIN PROCESSOR ———————————————————
def process_json_files(
    directory: Union[str, Path], backup: bool = True, dry_run: bool = False
) -> None:
    directory = Path(directory)
    if not directory.is_dir():
        raise NotADirectoryError(f"Directory not found: {directory}")

    json_files = list(directory.rglob("*.json"))
    print(f"Found {len(json_files)} JSON file(s)\n")

    for json_path in json_files:
        print(f"Processing: {json_path.name}")

        try:
            with open(json_path, encoding="utf-8") as f:
                data = json.load(f)

            new_data = deep_replace_account(copy.deepcopy(data))

            if dry_run:
                if data == new_data:
                    print("   No change\n")
                else:
                    print("   CHANGE DETECTED (dry run):")
                    pprint(data)
                    print("\n→ becomes →\n")
                    pprint(new_data)
                    print()
                continue

            # Safe write with backup
            backup_path = json_path.with_suffix(".json.bak")
            temp_path = json_path.with_suffix(".json.tmp")

            if backup:
                shutil.copy2(json_path, backup_path)

            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(new_data, f, indent=4, ensure_ascii=False)

            with open(temp_path, encoding="utf-8") as f:
                json.load(f)  # validate

            temp_path.replace(json_path)
            print(f"   SUCCESS: {json_path.name} updated\n")

        except Exception as e:
            print(f"   FAILED: {e}")
            if backup and backup_path.exists():
                shutil.copy2(backup_path, json_path)
                print("   Restored from backup")
            if temp_path.exists():
                temp_path.unlink(missing_ok=True)
            print()


# ——————————————————— USAGE ———————————————————
if __name__ == "__main__":
    TARGET = "/home/a/finance/receipt_labels"

    print("=== DRY RUN (RECOMMENDED FIRST) ===\n")
    # process_json_files(TARGET, backup=True, dry_run=True)

    print("\n=== REAL RUN (uncomment when ready) ===\n")
    process_json_files(TARGET, backup=True, dry_run=False)
