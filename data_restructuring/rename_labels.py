import os
from typing import List

from typeguard import typechecked


@typechecked
def rename_receipt_folders_to_hash_only(*, directory: str) -> List[str]:
    """
    Renames all subfolders in `directory` from:
        anything_<hash>
    to:
        <hash>

    It simply takes the part *after the last underscore* as the hash.
    """
    if not os.path.isdir(directory):
        raise ValueError(f"Directory not found: {directory}")

    renamed_folders = []

    for folder_name in os.listdir(directory):
        folder_path = os.path.join(directory, folder_name)

        if not os.path.isdir(folder_path):
            continue  # Skip files

        # Split on the LAST underscore
        if "_" not in folder_name:
            continue  # No underscore → not our format

        image_hash = folder_name.rsplit("_", 1)[-1]  # Everything after last _

        new_folder_name = image_hash
        new_folder_path = os.path.join(directory, new_folder_name)

        # Avoid overwriting existing folders
        if os.path.exists(new_folder_path):
            print(
                f"Warning: Skipping {folder_name} → {new_folder_name} (target"
                " exists)"
            )
            continue

        try:
            os.rename(folder_path, new_folder_path)
            renamed_folders.append(new_folder_path)
            print(f"Renamed: {folder_name} → {new_folder_name}")
        except OSError as e:
            print(f"Error: Could not rename {folder_name}: {e}")

    return renamed_folders


# Run it
if __name__ == "__main__":
    rename_receipt_folders_to_hash_only(
        directory="/home/a/finance/receipt_labels"
    )
