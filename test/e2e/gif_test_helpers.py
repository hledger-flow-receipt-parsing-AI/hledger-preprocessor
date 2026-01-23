"""Shared helpers for GIF generation tests."""

import os
import subprocess
import sys
from pathlib import Path

import pytest


def get_project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.parent.parent


def get_demo_env() -> dict:
    """Environment variables for running demos."""
    env = os.environ.copy()
    env["TERM"] = "xterm-256color"
    return env


def run_demo_script(
    script_path: Path,
    env: dict,
    config_path: Path | None = None,
    timeout: int = 60,
) -> subprocess.CompletedProcess:
    """Run a demo generation script and return the result.

    Args:
        script_path: Path to the generate.sh script
        env: Environment variables dict
        config_path: Optional config path (for scripts that need it)
        timeout: Timeout in seconds
    """
    cmd = ["bash", str(script_path)]
    if config_path is not None:
        cmd.append(str(config_path))

    print(f'\nRunning: {" ".join(cmd)}')

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        env=env,
    )

    if result.returncode != 0:
        print("--- STDOUT ---")
        print(result.stdout)
        print("--- STDERR ---", file=sys.stderr)
        print(result.stderr, file=sys.stderr)

    return result


def run_gif_test(
    temp_finance_root: dict,
    monkeypatch,
    demo_name: str,
    gif_subdir: str,
    timeout: int = 60,
    needs_config: bool = True,
) -> None:
    """Run a single GIF generation test.

    Args:
        temp_finance_root: Fixture with config_path and other paths
        monkeypatch: pytest monkeypatch fixture
        demo_name: Name of the demo (e.g., "01_setup_config")
        gif_subdir: Subdirectory under gifs/ containing generate.sh
        timeout: Timeout in seconds for the demo script
        needs_config: Whether the script needs config_path argument
    """
    project_root = get_project_root()
    monkeypatch.chdir(project_root)

    script_path = project_root / "gifs" / gif_subdir / "generate.sh"
    if not script_path.exists():
        pytest.skip(f"Script not found: {script_path}")

    config_path = temp_finance_root["config_path"] if needs_config else None

    result = run_demo_script(
        script_path=script_path,
        env=get_demo_env(),
        config_path=config_path,
        timeout=timeout,
    )

    assert result.returncode == 0, f"Demo failed: {result.stderr}"

    # Check GIF was created
    output_gif = (
        project_root / "gifs" / gif_subdir / "output" / f"{demo_name}.gif"
    )
    assert output_gif.exists(), f"GIF should exist at {output_gif}"
