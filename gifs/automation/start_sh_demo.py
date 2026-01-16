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
    import yaml

    conda_base = get_conda_base()

    # Parse config to find working directory
    with open(config_path) as f:
        config_data = yaml.safe_load(f)

    root_path = os.path.expanduser(
        config_data["dir_paths"]["root_finance_path"]
    )
    working_subdir = config_data["dir_paths"]["working_subdir"]
    working_dir = os.path.join(root_path, working_subdir)
    asset_csv_dir = os.path.join(working_dir, "asset_transaction_csvs")
    all_years_journal = os.path.join(working_dir, "all-years.journal")

    # Get start journal path if configured
    start_journal_path = config_data.get("dir_paths", {}).get(
        "start_journal_filepath", ""
    )
    if start_journal_path:
        start_journal_path = os.path.expanduser(start_journal_path)

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

    # =========================================================================
    # Step 1: Preprocess Assets
    # =========================================================================
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

    time.sleep(0.5)

    # Show generated CSV files
    print(f"\n{Colors.BOLD_CYAN}Generated CSV files:{Colors.RESET}")
    if os.path.exists(asset_csv_dir):
        show_file_tree(asset_csv_dir, max_depth=2)
    else:
        print(
            f"{Colors.GRAY}(asset_transaction_csvs directory not"
            f" created){Colors.RESET}"
        )

    time.sleep(1)

    # =========================================================================
    # Step 2: Run hledger-flow import
    # =========================================================================
    show_step(2, "Running hledger-flow import")
    print(
        f"{Colors.GRAY}Converting CSV files to hledger journal"
        f" format...{Colors.RESET}"
    )

    hledger_flow_cmd = (
        f"bash -c 'source {conda_base}/etc/profile.d/conda.sh && "
        "conda activate hledger_preprocessor && "
        f"cd {working_dir} && hledger-flow import'"
    )

    success = run_command_with_display(
        cmd=hledger_flow_cmd,
        description="Running: hledger-flow import",
        env=env,
        timeout=120,
    )

    if not success:
        print(
            f"{Colors.BOLD_YELLOW}⚠ hledger-flow import had issues, "
            f"continuing...{Colors.RESET}"
        )
        # Don't stop - hledger-flow may fail on empty data but we continue

    time.sleep(0.5)

    # Add starting position to all-years.journal if configured and exists
    if start_journal_path and os.path.exists(start_journal_path):
        if os.path.exists(all_years_journal):
            with open(all_years_journal) as f:
                content = f.read()
            include_line = f"include {start_journal_path}"
            if include_line not in content:
                print(
                    f"\n{Colors.GRAY}Adding starting position to"
                    f" all-years.journal...{Colors.RESET}"
                )
                with open(all_years_journal, "a") as f:
                    f.write(f"\n{include_line}\n")
                print(f"{Colors.GREEN}✓ Added: {include_line}{Colors.RESET}")
                time.sleep(0.5)

    # Show generated journal structure
    print(f"\n{Colors.BOLD_CYAN}Generated journal structure:{Colors.RESET}")
    if os.path.exists(working_dir):
        show_file_tree(working_dir, max_depth=3)

    time.sleep(1)

    # =========================================================================
    # Step 3: Generate plots with hledger_plot
    # =========================================================================
    show_step(3, "Generating Financial Plots")
    print(
        f"{Colors.GRAY}Creating SVG visualizations of financial"
        f" data...{Colors.RESET}"
    )

    # Only run hledger_plot if we have a journal file
    if os.path.exists(all_years_journal):
        hledger_plot_cmd = (
            f"bash -c 'source {conda_base}/etc/profile.d/conda.sh && "
            "conda activate hledger_preprocessor && "
            f"hledger_plot --config {config_path} "
            f"--journal-filepath {all_years_journal} -d EUR -es'"
        )

        success = run_command_with_display(
            cmd=hledger_plot_cmd,
            description="Running: hledger_plot (export sankey)",
            env=env,
            timeout=120,
        )

        if not success:
            print(
                f"{Colors.BOLD_YELLOW}⚠ hledger_plot had issues{Colors.RESET}"
            )
    else:
        print(
            f"{Colors.GRAY}(Skipping hledger_plot - no journal file"
            f" found){Colors.RESET}"
        )

    time.sleep(0.5)

    # Show generated plots
    hledger_plots_dir = os.path.join(working_dir, "hledger_plots")
    if os.path.exists(hledger_plots_dir):
        print(f"\n{Colors.BOLD_CYAN}Generated plot files:{Colors.RESET}")
        show_file_tree(hledger_plots_dir, max_depth=2)

    time.sleep(1)

    # =========================================================================
    # Final Summary
    # =========================================================================
    show_header("Pipeline Complete!")
    print()
    print(
        f"{Colors.BOLD_GREEN}✓ Full ./start.sh pipeline completed"
        f" successfully!{Colors.RESET}"
    )
    print()
    print(f"{Colors.WHITE}The pipeline has:{Colors.RESET}")
    print(
        f"{Colors.WHITE}  • Preprocessed assets (receipts → CSVs){Colors.RESET}"
    )
    print(
        f"{Colors.WHITE}  • Imported with hledger-flow (CSVs →"
        f" journals){Colors.RESET}"
    )
    print(f"{Colors.WHITE}  • Generated financial plots (SVGs){Colors.RESET}")
    print()

    # Show key output files
    print(f"{Colors.BOLD_CYAN}Key output files:{Colors.RESET}")
    if os.path.exists(all_years_journal):
        print(f"  {Colors.GREEN}✓{Colors.RESET} {all_years_journal}")
    if os.path.exists(hledger_plots_dir):
        svg_files = [
            f for f in os.listdir(hledger_plots_dir) if f.endswith(".svg")
        ]
        for svg in svg_files[:3]:  # Show first 3 SVGs
            print(
                f"  {Colors.GREEN}✓{Colors.RESET} "
                f"{os.path.join(hledger_plots_dir, svg)}"
            )
        if len(svg_files) > 3:
            print(
                f"  {Colors.GRAY}  ... and {len(svg_files) - 3} more"
                f"{Colors.RESET}"
            )

    print()
    print(
        f"{Colors.GRAY}To view the dashboard: hledger_plot --config"
        f" {config_path} -s{Colors.RESET}"
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
