#!/usr/bin/env python3
"""Pre-commit hook: check if committed changes require GIF re-recording.

Uses two data sources:
1. _coverage.json files (primary) — auto-generated Python execution traces
   from GIF recordings.  Lists every .py file executed during recording.
2. gif_dependencies.yaml (secondary) — manually maintained patterns for
   non-Python files (shell scripts, YAML fixtures, receipt images).

If a _coverage.json is MISSING for a GIF, the hook errors (forces re-record).
If a _coverage.json has type "standalone", empty files_touched is accepted.

Installation (in each sub-repo's .pre-commit-config.yaml):
    - repo: https://github.com/hledger-flow-receipt-parsing-AI/gif-staleness-hook  # noqa: E501
      rev: v0.1.0
      hooks:
        - id: check-gif-staleness
          args: [--bootstrap]  # remove once all GIFs have _coverage.json

Usage:
    check-gif-staleness.py [--ci] [--block] [--bootstrap]

    --ci         CI mode: compare HEAD~1..HEAD instead of staged files.
    --block      Exit 1 if stale GIFs found (default: warn only, exit 0).
    --bootstrap  Treat missing coverage files as warnings instead of errors.
"""
import argparse
import ast
import fnmatch
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

# Try yaml import; fall back to a minimal parser if unavailable.
try:
    import yaml
except ImportError:
    yaml = None  # type: ignore[assignment]


# ── Locating files ───────────────────────────────────────────────────


def find_hledger_root() -> Path:
    """Walk up from git toplevel to find the hledger/ parent dir."""
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        sys.exit("Not inside a git repository.")
    repo_root = Path(result.stdout.strip())

    # The parent of the sub-repo should be the hledger root.
    candidate = repo_root.parent
    if (candidate / "hledger-preprocessor").is_dir():
        return candidate

    # Maybe we're in the hledger root itself.
    if (repo_root / "hledger-preprocessor").is_dir():
        return repo_root

    sys.exit(f"Cannot find hledger mono-repo root from {repo_root}.")


def detect_sub_repo() -> str:
    """Return the directory name of the current git repo."""
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
    )
    return Path(result.stdout.strip()).name


# ── Git helpers ──────────────────────────────────────────────────────


def get_staged_files() -> List[str]:
    """Get staged file paths (relative to repo root)."""
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMRT"],
        capture_output=True,
        text=True,
    )
    return [f for f in result.stdout.strip().splitlines() if f]


def get_ci_changed_files() -> List[str]:
    """Get files changed in the last commit (for CI mode)."""
    result = subprocess.run(
        ["git", "diff", "--name-only", "HEAD~1..HEAD", "--diff-filter=ACMRT"],
        capture_output=True,
        text=True,
    )
    return [f for f in result.stdout.strip().splitlines() if f]


# ── Coverage JSON loading ────────────────────────────────────────────


def discover_coverage_jsons(
    hledger_root: Path,
) -> Dict[str, dict]:
    """Find all _coverage.json files in gifs/*/output/."""
    gifs_dir = hledger_root / "hledger-preprocessor" / "gifs"
    result: Dict[str, dict] = {}
    for cov_file in gifs_dir.glob("*/output/*_coverage.json"):
        try:
            data = json.loads(cov_file.read_text())
            gif_name = data.get("gif", cov_file.parent.parent.name)
            result[gif_name] = data
        except (json.JSONDecodeError, KeyError):
            continue
    return result


def discover_gif_dirs(hledger_root: Path) -> List[str]:
    """Find all GIF directory names (by looking for generate.sh)."""
    gifs_dir = hledger_root / "hledger-preprocessor" / "gifs"
    dirs = []
    for gen_sh in sorted(gifs_dir.glob("*/generate.sh")):
        dirs.append(gen_sh.parent.name)
    return dirs


# ── YAML dependency loading (non-Python files) ──────────────────────


def load_yaml_deps(deps_path: Path) -> dict:
    """Load gif_dependencies.yaml for non-Python watch patterns."""
    if not deps_path.exists():
        return {}
    if yaml is not None:
        with open(deps_path) as f:
            return yaml.safe_load(f) or {}
    # Minimal fallback parser.
    return _parse_yaml_minimal(deps_path)


def _parse_yaml_minimal(path: Path) -> dict:
    """Bare-minimum YAML parser for gif_dependencies.yaml."""
    import re

    text = path.read_text()
    result: dict = {"gifs": {}, "shared_automation": []}
    current_section: Optional[str] = None
    current_gif: Optional[str] = None
    current_key: Optional[str] = None

    for raw_line in text.splitlines():
        line = re.sub(r"(?<!\w)#.*", "", raw_line).rstrip()
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip())

        if indent == 0 and line.rstrip().endswith(":"):
            current_section = line.strip().rstrip(":")
            current_gif = None
            current_key = None
        elif indent == 2 and line.strip().startswith("- "):
            val = line.strip()[2:].strip()
            if current_section == "shared_automation":
                result.setdefault("shared_automation", []).append(val)
        elif indent == 2 and line.rstrip().endswith(":"):
            current_gif = line.strip().rstrip(":")
            if current_section == "gifs":
                result["gifs"][current_gif] = {}
        elif indent == 4 and current_gif and ":" in line:
            key, _, val = line.strip().partition(":")
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            if current_section == "gifs" and current_gif in result["gifs"]:
                if key == "watches":
                    result["gifs"][current_gif]["watches"] = []
                    current_key = "watches"
                else:
                    result["gifs"][current_gif][key] = val
                    current_key = None
        elif indent == 6 and line.strip().startswith("- "):
            val = line.strip()[2:].strip()
            if (
                current_section == "gifs"
                and current_gif
                and current_key == "watches"
            ):
                result["gifs"][current_gif].setdefault("watches", []).append(
                    val
                )

    return result


# ── AST hashing ──────────────────────────────────────────────────────


def compute_ast_hash(filepath: Path) -> Optional[str]:
    """Compute SHA-256 of a Python file's AST (ignores comments/whitespace).

    Returns None if the file is not .py, doesn't exist, or fails to parse.
    """
    if not filepath.suffix == ".py":
        return None
    try:
        source = filepath.read_text(encoding="utf-8")
        tree = ast.parse(source)
        return hashlib.sha256(ast.dump(tree).encode("utf-8")).hexdigest()
    except (SyntaxError, UnicodeDecodeError, FileNotFoundError, OSError):
        return None


# ── Matching ─────────────────────────────────────────────────────────


def match_path(filepath: str, pattern: str) -> bool:
    """Check if filepath matches a glob pattern (supports **)."""
    if "**" in pattern:
        prefix = pattern.split("**")[0]
        return filepath.startswith(prefix)
    return fnmatch.fnmatch(filepath, pattern)


def check_coverage_staleness(
    repo_name: str,
    changed_files: List[str],
    coverage_data: Dict[str, dict],
    hledger_root: Path,
) -> List[Tuple[str, str]]:
    """Check changed files against coverage traces (Python files).

    If the coverage JSON contains ast_hashes, compares the current AST
    hash of each changed file against the stored hash.  Only flags as
    stale when the AST actually differs (ignoring comments/whitespace).
    Falls back to "any change = stale" when ast_hashes is missing.
    """
    root_relative_files = [f"{repo_name}/{f}" for f in changed_files]
    stale = []
    for gif_name, cov in coverage_data.items():
        gif_type = cov.get("type", "config-dependent")
        files_touched: List[str] = cov.get("files_touched", [])
        ast_hashes: Dict[str, str] = cov.get("ast_hashes", {})

        if gif_type == "standalone" and not files_touched:
            continue

        touched_set: Set[str] = set(files_touched)
        for changed in root_relative_files:
            if changed not in touched_set:
                continue

            # If we have a stored AST hash, compare against current.
            stored_hash = ast_hashes.get(changed)
            if stored_hash is not None:
                current_hash = compute_ast_hash(hledger_root / changed)
                if current_hash == stored_hash:
                    # AST unchanged — skip (comment/whitespace only).
                    continue
                if current_hash is None:
                    # File deleted or unparseable — treat as stale.
                    desc = f"cannot parse {changed} (deleted or syntax error)"
                else:
                    desc = f"AST changed in {changed}"
            else:
                # No stored hash — fall back to any-change-is-stale.
                desc = f"coverage trace includes {changed}"

            stale.append((gif_name, desc))
            break

    return stale


def check_yaml_staleness(
    repo_name: str,
    changed_files: List[str],
    yaml_deps: dict,
) -> List[Tuple[str, str]]:
    """Check changed files against YAML watch patterns (non-Python files)."""
    if not yaml_deps:
        return []

    root_relative_files = [f"{repo_name}/{f}" for f in changed_files]
    stale = []
    gifs = yaml_deps.get("gifs", {})

    # Shared automation patterns affect all GIFs.
    shared_patterns = yaml_deps.get("shared_automation", [])
    shared_hit = any(
        match_path(f, pat)
        for f in root_relative_files
        for pat in shared_patterns
    )

    for gif_name, gif_info in gifs.items():
        if not isinstance(gif_info, dict):
            continue

        if shared_hit:
            stale.append(
                (gif_name, gif_info.get("description", "shared automation"))
            )
            continue

        watches = gif_info.get("watches", [])
        for pattern in watches:
            if any(match_path(f, pattern) for f in root_relative_files):
                stale.append((gif_name, gif_info.get("description", pattern)))
                break

    return stale


def check_gif_artifacts_staged(
    stale_gifs: List[Tuple[str, str]],
    staged_files: List[str],
) -> List[Tuple[str, str]]:
    """Filter out GIFs whose artifacts are also being committed."""
    not_rerecorded = []
    for gif_name, desc in stale_gifs:
        artifact_patterns = [
            f"gifs/{gif_name}/output/*",
            f"gifs/{gif_name}/recordings/*",
        ]
        rerecorded = any(
            match_path(f, pat)
            for f in staged_files
            for pat in artifact_patterns
        )
        if not rerecorded:
            not_rerecorded.append((gif_name, desc))
    return not_rerecorded


# ── Output ───────────────────────────────────────────────────────────


def print_missing_coverage(missing: List[str], bootstrap: bool) -> None:
    """Print error/warning for GIFs missing coverage data."""
    sep = "=" * 60
    label = "WARNING" if bootstrap else "ERROR"
    print(f"\n{sep}")
    print(f"GIF COVERAGE {label}")
    print(sep)
    print("These GIFs have no _coverage.json (re-record to generate):\n")
    for name in missing:
        print(f"  - {name}")
    print("\nRe-record from hledger-preprocessor:")
    for name in missing:
        print(f"  ./build_userstories.sh --gif {name}")
    print(f"{sep}\n")


def print_stale_warning(
    repo_name: str,
    stale_gifs: List[Tuple[str, str]],
    is_preprocessor: bool,
) -> None:
    """Print a human-readable staleness warning."""
    sep = "=" * 60
    print(f"\n{sep}")
    print("GIF STALENESS WARNING")
    print(sep)

    if is_preprocessor:
        print("These GIFs may be stale and were NOT re-recorded:\n")
    else:
        print(f"Changes in {repo_name}/ may invalidate these GIFs:\n")

    for name, desc in stale_gifs:
        print(f"  - {name}: {desc}")

    print("\nRe-record from hledger-preprocessor:")
    # Deduplicate names (a GIF might appear from both coverage + yaml).
    seen = set()
    for name, _ in stale_gifs:
        if name not in seen:
            print(f"  ./build_userstories.sh --gif {name}")
            seen.add(name)

    print(f"{sep}\n")


# ── Main ─────────────────────────────────────────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser(description="Check GIF staleness.")
    parser.add_argument(
        "--ci",
        action="store_true",
        help="CI mode: compare HEAD~1..HEAD instead of staged files.",
    )
    parser.add_argument(
        "--block",
        action="store_true",
        help="Exit 1 if stale GIFs found (default: warn only).",
    )
    parser.add_argument(
        "--bootstrap",
        action="store_true",
        help="Treat missing coverage as warnings instead of errors.",
    )
    args = parser.parse_args()

    hledger_root = find_hledger_root()
    repo_name = detect_sub_repo()

    # Get changed files.
    if args.ci:
        changed_files = get_ci_changed_files()
    else:
        changed_files = get_staged_files()

    if not changed_files:
        return 0

    exit_code = 0

    # ── Check for missing coverage files ──
    all_gif_dirs = discover_gif_dirs(hledger_root)
    coverage_data = discover_coverage_jsons(hledger_root)
    missing_coverage = [d for d in all_gif_dirs if d not in coverage_data]

    if missing_coverage:
        print_missing_coverage(missing_coverage, args.bootstrap)
        if not args.bootstrap:
            exit_code = 1  # Hard fail: coverage must exist.

    # ── Check Python files against coverage traces ──
    stale_from_coverage = check_coverage_staleness(
        repo_name, changed_files, coverage_data, hledger_root
    )

    # ── Check non-Python files against YAML deps ──
    yaml_deps_path = (
        hledger_root / "hledger-preprocessor" / "gif_dependencies.yaml"
    )
    yaml_deps = load_yaml_deps(yaml_deps_path)
    stale_from_yaml = check_yaml_staleness(repo_name, changed_files, yaml_deps)

    # ── Merge and deduplicate ──
    all_stale: Dict[str, str] = {}
    for name, desc in stale_from_coverage + stale_from_yaml:
        if name not in all_stale:
            all_stale[name] = desc
    stale_list = list(all_stale.items())

    if not stale_list:
        return exit_code

    # In hledger-preprocessor, check if artifacts were also committed.
    is_preprocessor = repo_name == "hledger-preprocessor"
    if is_preprocessor and not args.ci:
        stale_list = check_gif_artifacts_staged(stale_list, changed_files)
        if not stale_list:
            return exit_code

    print_stale_warning(repo_name, stale_list, is_preprocessor)
    if args.block:
        exit_code = 1
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
