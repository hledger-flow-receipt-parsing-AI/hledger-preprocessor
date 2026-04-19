#!/usr/bin/env python3
"""Install or uninstall the coverage autostart .pth file in the active conda env.

The .pth file makes every Python subprocess call coverage.process_startup()
on startup.  Combined with the COVERAGE_PROCESS_START environment variable
pointing to a .coveragerc, this enables automatic coverage tracing of all
Python child processes (including those spawned by pexpect/subprocess).

Usage:
    python -m gifs.automation.install_coverage_pth --install
    python -m gifs.automation.install_coverage_pth --uninstall
    python -m gifs.automation.install_coverage_pth --status
"""
import argparse
import sys
import sysconfig
from pathlib import Path

PTH_FILENAME = "coverage_autostart.pth"
PTH_CONTENT = "import coverage; coverage.process_startup()\n"


def get_pth_path() -> Path:
    """Return the path where the .pth file should be installed."""
    site_packages = sysconfig.get_paths()["purelib"]
    return Path(site_packages) / PTH_FILENAME


def install() -> int:
    """Install the .pth file."""
    pth = get_pth_path()
    pth.write_text(PTH_CONTENT)
    print(f"Installed: {pth}")
    return 0


def uninstall() -> int:
    """Remove the .pth file if it exists."""
    pth = get_pth_path()
    if pth.exists():
        pth.unlink()
        print(f"Removed: {pth}")
    else:
        print(f"Not installed: {pth}")
    return 0


def status() -> int:
    """Check whether the .pth file is installed."""
    pth = get_pth_path()
    if pth.exists():
        print(f"Installed: {pth}")
        return 0
    else:
        print(f"Not installed (expected at: {pth})")
        return 1


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Manage the coverage autostart .pth file."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--install", action="store_true")
    group.add_argument("--uninstall", action="store_true")
    group.add_argument("--status", action="store_true")
    args = parser.parse_args()

    if args.install:
        return install()
    elif args.uninstall:
        return uninstall()
    else:
        return status()


if __name__ == "__main__":
    sys.exit(main())
