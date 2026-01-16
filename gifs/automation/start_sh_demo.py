#!/usr/bin/env python3
"""Start.sh pipeline demo automation - demonstrates the full pipeline."""

import os
import subprocess
import time
from typing import Optional

from .core import Colors, Screen, get_conda_base


def run_command_with_display(
    *,
    cmd: str,
    description: str,
    working_dir: Optional[str] = None,
    env: Optional[dict] = None,
    timeout: int = 120,
) -> bool:
    """Run a command and display its output in real-time.

    Args:
        cmd: The command to run
        description: Description to show before running
        working_dir: Working directory for the command
        env: Environment variables
        timeout: Timeout in seconds

    Returns:
        True if command succeeded, False otherwise
    """
    print(f"\n{Colors.BOLD_CYAN}{'─'*70}{Colors.RESET}")
    print(f"{Colors.BOLD_CYAN}  {description}{Colors.RESET}")
    print(f"{Colors.BOLD_CYAN}{'─'*70}{Colors.RESET}")
    print()
    print(f"{Colors.BOLD_BLUE}$ {cmd}{Colors.RESET}")
    print()
    time.sleep(0.5)

    try:
        process = subprocess.Popen(
            cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            cwd=working_dir,
            env=env,
        )

        # Stream output
        for line in iter(process.stdout.readline, ""):
            print(f"{Colors.WHITE}{line}{Colors.RESET}", end="")
            time.sleep(0.02)  # Small delay to make output readable

        process.wait(timeout=timeout)

        if process.returncode == 0:
            print(f"\n{Colors.BOLD_GREEN}✓ Success{Colors.RESET}")
            return True
        else:
            print(
                f"\n{Colors.BOLD_RED}✗ Failed with code"
                f" {process.returncode}{Colors.RESET}"
            )
            return False

    except subprocess.TimeoutExpired:
        process.kill()
        print(f"\n{Colors.BOLD_RED}✗ Timeout after {timeout}s{Colors.RESET}")
        return False
    except Exception as e:
        print(f"\n{Colors.BOLD_RED}✗ Error: {e}{Colors.RESET}")
        return False


def show_header(title: str) -> None:
    """Display a section header."""
    print()
    print(f"{Colors.BOLD_YELLOW}{'═'*70}{Colors.RESET}")
    print(f"{Colors.BOLD_YELLOW}  {title}{Colors.RESET}")
    print(f"{Colors.BOLD_YELLOW}{'═'*70}{Colors.RESET}")
    time.sleep(1)


def show_step(step_num: int, description: str) -> None:
    """Display a step indicator."""
    print()
    print(f"{Colors.BOLD_MAGENTA}[Step {step_num}] {description}{Colors.RESET}")
    time.sleep(0.5)


def show_file_tree(directory: str, max_depth: int = 3) -> None:
    """Show a simplified file tree of the directory."""
    print(
        f"\n{Colors.BOLD_BLUE}$ tree -L {max_depth} {directory}{Colors.RESET}"
    )
    print()
    try:
        result = subprocess.run(
            ["tree", "-L", str(max_depth), directory],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            print(f"{Colors.WHITE}{result.stdout}{Colors.RESET}")
        else:
            # Fallback to ls if tree not available
            result = subprocess.run(
                ["ls", "-la", directory],
                capture_output=True,
                text=True,
            )
            print(f"{Colors.WHITE}{result.stdout}{Colors.RESET}")
    except Exception:
        print(f"{Colors.GRAY}(could not list directory){Colors.RESET}")
    time.sleep(1)


def run_start_sh_demo(config_path: str) -> None:
    """Run the start.sh pipeline demo.

    This demonstrates the complete hledger-preprocessor pipeline:
    1. Preprocess assets (convert receipts to CSVs)
    2. Run hledger-flow import (convert CSVs to journals)
    3. Generate plots (create SVG visualizations)

    Args:
        config_path: Path to the hledger-preprocessor config file
    """
    conda_base = get_conda_base()

    # Setup environment
    env = os.environ.copy()
    env["TERM"] = "xterm-256color"
    env["SKIP_DASH"] = "true"  # Skip blocking Dash app for demo

    Screen.clear()

    # Title
    show_header("hledger-preprocessor: Full Pipeline Demo")
    print()
    print(
        f"{Colors.WHITE}This demo shows the complete ./start.sh"
        f" workflow:{Colors.RESET}"
    )
    print(
        f"{Colors.WHITE}  1. Preprocess assets (receipts → CSVs){Colors.RESET}"
    )
    print(
        f"{Colors.WHITE}  2. Import with hledger-flow (CSVs →"
        f" journals){Colors.RESET}"
    )
    print(f"{Colors.WHITE}  3. Generate financial plots (SVGs){Colors.RESET}")
    print()
    time.sleep(2)

    # Step 1: Preprocess Assets
    show_step(1, "Preprocessing Assets")
    print(
        f"{Colors.GRAY}Converting receipt data to CSV files for"
        f" asset accounts...{Colors.RESET}"
    )

    preprocess_cmd = (
        f"bash -c 'source {conda_base}/etc/profile.d/conda.sh && "
        "conda activate hledger_preprocessor && "
        f"hledger_preprocessor --config {config_path} --preprocess-assets'"
    )

    success = run_command_with_display(
        cmd=preprocess_cmd,
        description="Running: hledger_preprocessor --preprocess-assets",
        env=env,
        timeout=60,
    )

    if not success:
        print(f"{Colors.BOLD_RED}Pipeline stopped due to error{Colors.RESET}")
        return

    time.sleep(1)

    # Step 2: Show generated files
    show_step(2, "Verifying Generated Files")

    # Parse config to find working directory
    import yaml

    with open(config_path) as f:
        config_data = yaml.safe_load(f)

    root_path = os.path.expanduser(
        config_data["dir_paths"]["root_finance_path"]
    )
    working_subdir = config_data["dir_paths"]["working_subdir"]
    working_dir = os.path.join(root_path, working_subdir)
    asset_csv_dir = os.path.join(working_dir, "asset_transaction_csvs")

    if os.path.exists(asset_csv_dir):
        show_file_tree(asset_csv_dir, max_depth=3)
    else:
        print(
            f"{Colors.GRAY}(asset_transaction_csvs directory not"
            f" created){Colors.RESET}"
        )

    time.sleep(1)

    # Step 3: Show success summary
    show_header("Pipeline Complete!")
    print()
    print(
        f"{Colors.BOLD_GREEN}✓ Assets preprocessed successfully{Colors.RESET}"
    )
    print()
    print(f"{Colors.WHITE}The pipeline has:{Colors.RESET}")
    print(
        f"{Colors.WHITE}  • Converted receipt data to CSV format{Colors.RESET}"
    )
    print(
        f"{Colors.WHITE}  • Generated files ready for"
        f" hledger-flow import{Colors.RESET}"
    )
    print()
    print(
        f"{Colors.GRAY}Next steps: Run hledger-flow import and"
        f" hledger_plot{Colors.RESET}"
    )
    print()
    time.sleep(3)


def main() -> None:
    """Main entry point when run as a script."""
    config_path = os.environ.get("CONFIG_FILEPATH")
    if not config_path:
        print(
            f"{Colors.BOLD_RED}Error: CONFIG_FILEPATH environment variable"
            f" not set{Colors.RESET}"
        )
        return

    run_start_sh_demo(config_path)


if __name__ == "__main__":
    main()
