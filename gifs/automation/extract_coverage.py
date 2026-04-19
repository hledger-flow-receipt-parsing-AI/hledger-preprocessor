#!/usr/bin/env python3
"""Extract coverage data from a GIF recording into a portable JSON file.

After a GIF is recorded with coverage enabled, this script:
1. Combines parallel .coverage.* files from /tmp/gif_coverage/
2. Extracts the list of measured Python files
3. Strips the hledger root prefix to produce repo-relative paths
4. Writes a _coverage.json sidecar next to the GIF output

Usage:
    python -m gifs.automation.extract_coverage \
        --gif-name 2b_label_receipt \
        --output gifs/2b_label_receipt/output/2b_label_receipt_coverage.json \
        [--type config-dependent] \
        [--hledger-root /home/a/git/git/hledger] \
        [--coverage-dir /tmp/gif_coverage]
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional


HLEDGER_ROOT_DEFAULT = "/home/a/git/git/hledger"
COVERAGE_DIR_DEFAULT = "/tmp/gif_coverage"


def combine_coverage(coverage_dir: str) -> Optional["coverage.CoverageData"]:
    """Combine parallel .coverage.* files and return the merged data."""
    import coverage

    cov = coverage.Coverage(data_file=os.path.join(coverage_dir, ".coverage"))
    cov.combine(data_paths=[coverage_dir], keep=False)
    return cov.get_data()


def extract_files(
    cov_data: "coverage.CoverageData",
    hledger_root: str,
) -> List[str]:
    """Extract measured files as hledger-root-relative paths.

    Only includes files under hledger_root. Strips the root prefix so paths
    look like "hledger-config/src/hledger_config/arg_parser.py".
    """
    root = hledger_root.rstrip("/") + "/"
    files = []
    for filepath in sorted(cov_data.measured_files()):
        if filepath.startswith(root):
            relative = filepath[len(root):]
            files.append(relative)
    return files


def write_coverage_json(
    output_path: str,
    gif_name: str,
    gif_type: str,
    files_touched: List[str],
) -> None:
    """Write the coverage JSON sidecar."""
    data = {
        "gif": gif_name,
        "type": gif_type,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "files_touched": files_touched,
    }
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"Coverage: {len(files_touched)} files → {output_path}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Extract GIF recording coverage into a JSON sidecar."
    )
    parser.add_argument(
        "--gif-name",
        required=True,
        help="Name of the GIF (e.g. 2b_label_receipt).",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Output path for the _coverage.json file.",
    )
    parser.add_argument(
        "--type",
        default="config-dependent",
        choices=["standalone", "config-dependent"],
        help="GIF type. Standalone GIFs may have empty coverage.",
    )
    parser.add_argument(
        "--hledger-root",
        default=HLEDGER_ROOT_DEFAULT,
        help="Root directory of the hledger mono-repo.",
    )
    parser.add_argument(
        "--coverage-dir",
        default=COVERAGE_DIR_DEFAULT,
        help="Directory containing .coverage.* parallel files.",
    )
    args = parser.parse_args()

    coverage_dir = args.coverage_dir

    # Check for coverage data files.
    coverage_files = list(Path(coverage_dir).glob(".coverage.*"))
    if not coverage_files:
        if args.type == "standalone":
            # Standalone GIFs don't execute hledger code — empty coverage is OK.
            write_coverage_json(args.output, args.gif_name, args.type, [])
            return 0
        print(
            f"WARNING: No coverage data found in {coverage_dir}. "
            f"Was COVERAGE_PROCESS_START set during recording?",
            file=sys.stderr,
        )
        # Still write empty JSON so the file exists (hook will see 0 files).
        write_coverage_json(args.output, args.gif_name, args.type, [])
        return 1

    try:
        cov_data = combine_coverage(coverage_dir)
    except Exception as e:
        print(f"ERROR combining coverage: {e}", file=sys.stderr)
        return 1

    files = extract_files(cov_data, args.hledger_root)
    write_coverage_json(args.output, args.gif_name, args.type, files)
    return 0


if __name__ == "__main__":
    sys.exit(main())
