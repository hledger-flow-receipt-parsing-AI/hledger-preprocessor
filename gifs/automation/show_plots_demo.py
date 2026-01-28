#!/usr/bin/env python3
"""Show plots demo - demonstrates hledger_plot visualizations."""

import os
import subprocess
import time

import yaml

from .core import Colors, Screen, get_conda_base


def print_header(title: str) -> None:
    """Print a section header."""
    print()
    print(f"{Colors.BOLD_YELLOW}{'═' * 70}{Colors.RESET}")
    print(f"{Colors.BOLD_YELLOW}  {title}{Colors.RESET}")
    print(f"{Colors.BOLD_YELLOW}{'═' * 70}{Colors.RESET}")
    print()
    time.sleep(1)


def print_subheader(title: str) -> None:
    """Print a subsection header."""
    print()
    print(f"{Colors.BOLD_CYAN}{'─' * 60}{Colors.RESET}")
    print(f"{Colors.BOLD_CYAN}  {title}{Colors.RESET}")
    print(f"{Colors.BOLD_CYAN}{'─' * 60}{Colors.RESET}")
    print()
    time.sleep(0.5)


def show_intro() -> None:
    """Show introduction to hledger_plot."""
    print(
        f"{Colors.WHITE}hledger_plot creates interactive financial"
        f" visualizations:{Colors.RESET}"
    )
    print()
    print(
        f"  {Colors.CYAN}•{Colors.RESET} {Colors.WHITE}Sankey"
        f" diagrams{Colors.RESET} - Show money flow between accounts"
    )
    print(
        f"  {Colors.CYAN}•{Colors.RESET} {Colors.WHITE}Treemap"
        f" plots{Colors.RESET} - Show hierarchical spending breakdown"
    )
    print()
    time.sleep(1.5)


def show_export_commands(config_path: str, journal_path: str) -> None:
    """Show the export commands."""
    print_subheader("Export Static SVG Files")

    print(
        f"{Colors.GRAY}Generate SVG files for embedding in"
        f" reports:{Colors.RESET}"
    )
    print()

    # Sankey export
    print(
        f"{Colors.BOLD_BLUE}$ hledger_plot --config"
        f" {os.path.basename(config_path)} \\{Colors.RESET}"
    )
    print(
        f"{Colors.BOLD_BLUE}    --journal-filepath"
        f" {os.path.basename(journal_path)} \\{Colors.RESET}"
    )
    print(f"{Colors.BOLD_BLUE}    -d EUR --export-sankey{Colors.RESET}")
    print()
    time.sleep(0.5)

    print(
        f"  {Colors.GREEN}→{Colors.RESET} Creates:"
        f" {Colors.YELLOW}hledger_plots/sankey_*.svg{Colors.RESET}"
    )
    print()
    time.sleep(0.5)

    # Treemap export
    print(
        f"{Colors.BOLD_BLUE}$ hledger_plot --config"
        f" {os.path.basename(config_path)} \\{Colors.RESET}"
    )
    print(
        f"{Colors.BOLD_BLUE}    --journal-filepath"
        f" {os.path.basename(journal_path)} \\{Colors.RESET}"
    )
    print(f"{Colors.BOLD_BLUE}    -d EUR --export-treemap{Colors.RESET}")
    print()
    time.sleep(0.5)

    print(
        f"  {Colors.GREEN}→{Colors.RESET} Creates:"
        f" {Colors.YELLOW}hledger_plots/treemap_*.svg{Colors.RESET}"
    )
    print()
    time.sleep(1)


def show_dashboard_command(config_path: str, journal_path: str) -> None:
    """Show the interactive dashboard command."""
    print_subheader("Interactive Dashboard")

    print(f"{Colors.GRAY}Launch the interactive Dash dashboard:{Colors.RESET}")
    print()

    print(
        f"{Colors.BOLD_BLUE}$ hledger_plot --config"
        f" {os.path.basename(config_path)} \\{Colors.RESET}"
    )
    print(
        f"{Colors.BOLD_BLUE}    --journal-filepath"
        f" {os.path.basename(journal_path)} \\{Colors.RESET}"
    )
    print(f"{Colors.BOLD_BLUE}    -d EUR --show-plots{Colors.RESET}")
    print()
    time.sleep(0.5)

    print(
        f"  {Colors.GREEN}→{Colors.RESET} Opens browser at"
        f" {Colors.CYAN}http://127.0.0.1:8050{Colors.RESET}"
    )
    print()
    time.sleep(1)


def show_sankey_diagram() -> None:
    """Show ASCII representation of Sankey diagram."""
    print_subheader("Sankey Diagram: Money Flow")

    print(
        f"{Colors.WHITE}Shows how money flows between accounts:{Colors.RESET}"
    )
    print()

    # ASCII art representation of Sankey
    print(f"  {Colors.GREEN}Income{Colors.RESET}")
    print(f"    {Colors.GRAY}│{Colors.RESET}")
    print(
        f"    {Colors.GRAY}├──────────────────────────────────────┐{Colors.RESET}"
    )
    print(
        f"    {Colors.GRAY}│{Colors.RESET}                                     "
        f" {Colors.GRAY}│{Colors.RESET}"
    )
    print(
        f"    {Colors.GRAY}▼{Colors.RESET}                                     "
        f" {Colors.GRAY}▼{Colors.RESET}"
    )
    print(
        f"  {Colors.CYAN}Assets:Checking{Colors.RESET}                   "
        f" {Colors.YELLOW}Expenses{Colors.RESET}"
    )
    print(
        f"    {Colors.GRAY}│{Colors.RESET}                                     "
        f" {Colors.GRAY}│{Colors.RESET}"
    )
    print(
        f"    {Colors.GRAY}│{Colors.RESET}                         "
        f" {Colors.GRAY}┌──────────┼──────────┐{Colors.RESET}"
    )
    print(
        f"    {Colors.GRAY}│{Colors.RESET}                         "
        f" {Colors.GRAY}│{Colors.RESET}          {Colors.GRAY}│{Colors.RESET}  "
        f"        {Colors.GRAY}│{Colors.RESET}"
    )
    print(
        f"    {Colors.GRAY}▼{Colors.RESET}                         "
        f" {Colors.GRAY}▼{Colors.RESET}          {Colors.GRAY}▼{Colors.RESET}  "
        f"        {Colors.GRAY}▼{Colors.RESET}"
    )
    print(
        f"  {Colors.MAGENTA}Savings{Colors.RESET}                 "
        f" {Colors.RED}Groceries{Colors.RESET}  {Colors.RED}Rent{Colors.RESET} "
        f"   {Colors.RED}Other{Colors.RESET}"
    )
    print()
    time.sleep(2)


def show_treemap_diagram() -> None:
    """Show ASCII representation of Treemap."""
    print_subheader("Treemap: Spending Breakdown")

    print(
        f"{Colors.WHITE}Shows hierarchical breakdown of expenses:{Colors.RESET}"
    )
    print()

    # ASCII art representation of Treemap
    print(
        f"  {Colors.GRAY}┌─────────────────────────────────────────────────────┐{Colors.RESET}"
    )
    print(
        f"  {Colors.GRAY}│{Colors.RESET} {Colors.BOLD_WHITE}Expenses{Colors.RESET} "
        "                                          "
        f" {Colors.GRAY}│{Colors.RESET}"
    )
    print(
        f"  {Colors.GRAY}├─────────────────────────┬───────────────────────────┤{Colors.RESET}"
    )
    print(
        f"  {Colors.GRAY}│{Colors.RESET} {Colors.YELLOW}Rent{Colors.RESET}     "
        "              "
        f" {Colors.GRAY}│{Colors.RESET} {Colors.CYAN}Groceries{Colors.RESET}   "
        f"              {Colors.GRAY}│{Colors.RESET}"
    )
    print(
        f"  {Colors.GRAY}│{Colors.RESET}   €800/mo               "
        f" {Colors.GRAY}│{Colors.RESET}   €300/mo                "
        f" {Colors.GRAY}│{Colors.RESET}"
    )
    print(
        f"  {Colors.GRAY}│{Colors.RESET}                         "
        f" {Colors.GRAY}├─────────────┬─────────────┤{Colors.RESET}"
    )
    print(
        f"  {Colors.GRAY}│{Colors.RESET}                         "
        f" {Colors.GRAY}│{Colors.RESET} {Colors.GREEN}ekoplaza{Colors.RESET}   "
        f" {Colors.GRAY}│{Colors.RESET} {Colors.GREEN}other{Colors.RESET}      "
        f" {Colors.GRAY}│{Colors.RESET}"
    )
    print(
        f"  {Colors.GRAY}│{Colors.RESET}                         "
        f" {Colors.GRAY}│{Colors.RESET}   €150     "
        f" {Colors.GRAY}│{Colors.RESET}   €150     "
        f" {Colors.GRAY}│{Colors.RESET}"
    )
    print(
        f"  {Colors.GRAY}├─────────────────────────┴─────────────┴─────────────┤{Colors.RESET}"
    )
    print(
        f"  {Colors.GRAY}│{Colors.RESET} {Colors.MAGENTA}Utilities{Colors.RESET} "
        f" {Colors.GRAY}│{Colors.RESET} {Colors.MAGENTA}Transport{Colors.RESET} {Colors.GRAY}│{Colors.RESET} {Colors.MAGENTA}Entertainment{Colors.RESET} "
        f"           {Colors.GRAY}│{Colors.RESET}"
    )
    print(
        f"  {Colors.GRAY}│{Colors.RESET}   €100    "
        f" {Colors.GRAY}│{Colors.RESET}   €80     "
        f" {Colors.GRAY}│{Colors.RESET}   €50                   "
        f" {Colors.GRAY}│{Colors.RESET}"
    )
    print(
        f"  {Colors.GRAY}└────────────┴───────────┴─────────────────────────────┘{Colors.RESET}"
    )
    print()
    time.sleep(2)


def run_actual_export(config_path: str, journal_path: str) -> None:
    """Run the actual export command and show results."""
    print_subheader("Running Export...")

    conda_base = get_conda_base()

    # Run sankey export
    cmd = (
        f"bash -c 'source {conda_base}/etc/profile.d/conda.sh && "
        "conda activate hledger_preprocessor && "
        f"hledger_plot --config {config_path} "
        f"--journal-filepath {journal_path} -d EUR -es -et'"
    )

    print(f"{Colors.BOLD_BLUE}$ hledger_plot -es -et{Colors.RESET}")
    print()
    time.sleep(0.5)

    env = os.environ.copy()
    env["TERM"] = "xterm-256color"
    env["SKIP_DASH"] = "true"  # Skip Dash dashboard launch for export-only

    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=60,
            env=env,
        )

        if result.returncode == 0:
            print(f"{Colors.GREEN}✓ Export successful{Colors.RESET}")
        else:
            print(
                f"{Colors.YELLOW}⚠ Export completed with warnings{Colors.RESET}"
            )

    except subprocess.TimeoutExpired:
        print(f"{Colors.YELLOW}⚠ Export timed out{Colors.RESET}")
    except Exception as e:
        print(f"{Colors.YELLOW}⚠ Export skipped: {e}{Colors.RESET}")

    print()
    time.sleep(0.5)


def show_generated_files(working_dir: str) -> None:
    """Show the generated plot files."""
    print_subheader("Generated Files")

    plots_dir = os.path.join(working_dir, "hledger_plots")

    if os.path.exists(plots_dir):
        svg_files = [f for f in os.listdir(plots_dir) if f.endswith(".svg")]

        if svg_files:
            print(f"{Colors.WHITE}SVG files ready for embedding:{Colors.RESET}")
            print()
            for svg in sorted(svg_files)[:6]:
                print(
                    f"  {Colors.GREEN}✓{Colors.RESET} {Colors.CYAN}{svg}{Colors.RESET}"
                )
                time.sleep(0.2)

            if len(svg_files) > 6:
                print(
                    f"  {Colors.GRAY}... and"
                    f" {len(svg_files) - 6} more{Colors.RESET}"
                )
            print()
        else:
            print(f"{Colors.GRAY}(No SVG files generated yet){Colors.RESET}")
            print()
    else:
        print(f"{Colors.GRAY}(hledger_plots directory not found){Colors.RESET}")
        print()

    time.sleep(1)


def show_summary() -> None:
    """Show summary."""
    print_subheader("Summary")

    print(f"{Colors.BOLD_GREEN}hledger_plot provides:{Colors.RESET}")
    print()
    print(
        f"  {Colors.GREEN}✓{Colors.RESET} {Colors.WHITE}Sankey diagrams for"
        f" money flow visualization{Colors.RESET}"
    )
    print(
        f"  {Colors.GREEN}✓{Colors.RESET} {Colors.WHITE}Treemap plots for"
        f" hierarchical spending{Colors.RESET}"
    )
    print(
        f"  {Colors.GREEN}✓{Colors.RESET} {Colors.WHITE}Interactive Dash"
        f" dashboard (-s flag){Colors.RESET}"
    )
    print(
        f"  {Colors.GREEN}✓{Colors.RESET} {Colors.WHITE}Static SVG export for"
        f" reports (-es, -et flags){Colors.RESET}"
    )
    print(
        f"  {Colors.GREEN}✓{Colors.RESET} {Colors.WHITE}Randomized data for"
        f" demos (-r flag){Colors.RESET}"
    )
    print()
    time.sleep(1)


def run_show_plots_demo(config_path: str) -> None:
    """Run the show plots demo."""
    Screen.clear()

    print_header("Bonus: Visualize Your Finances")

    # Parse config to find paths
    with open(config_path) as f:
        config_data = yaml.safe_load(f)

    root_path = os.path.expanduser(
        config_data["dir_paths"]["root_finance_path"]
    )
    working_subdir = config_data["dir_paths"]["working_subdir"]
    working_dir = os.path.join(root_path, working_subdir)
    journal_path = os.path.join(working_dir, "all-years.journal")

    show_intro()
    show_sankey_diagram()
    show_treemap_diagram()
    show_export_commands(config_path, journal_path)
    show_dashboard_command(config_path, journal_path)

    # Try to run actual export if journal exists
    if os.path.exists(journal_path):
        run_actual_export(config_path, journal_path)
        show_generated_files(working_dir)

    show_summary()

    print(f"{Colors.BOLD_GREEN}✓ Visualization demo complete!{Colors.RESET}")
    print()
    time.sleep(2)


def main() -> None:
    """Main entry point."""
    config_path = os.environ.get("CONFIG_FILEPATH", "config.yaml")
    run_show_plots_demo(config_path)


if __name__ == "__main__":
    main()
