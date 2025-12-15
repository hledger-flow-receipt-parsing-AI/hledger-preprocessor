# tests/test_cli_integration.py
import subprocess
import textwrap
from pathlib import Path


def test_cli_tui_recording(temp_finance_root, monkeypatch, tmp_path):
    monkeypatch.chdir(Path(__file__).parent.parent)

    tape_file = tmp_path / "demo.tape"
    output_gif = Path("docs") / "cli-demo.gif"  # or tmp_path / "cli.gif"
    output_gif.parent.mkdir(parents=True, exist_ok=True)

    tape_content = textwrap.dedent(
        f"""
    Set Width 80
    Set Height 24
    Set TypingSpeed 0.05s
    Set Theme "Catppuccin Mocha"

    # Start your CLI
    Run python -m hledger_preprocessor.cli --config {temp_finance_root["config_path"]} --verbose

    # Wait for the welcome message
    Sleep 2s

    # Simulate user actions
    Type "h"    # press h for help, or whatever your TUI uses
    Sleep 1s
    Type "q"    # quit
    Enter
    Sleep 500ms

    # Exit the program
    Ctrl+C
    Sleep 500ms
    """
    )

    tape_file.write_text(tape_content)

    # Run vhs – this generates the GIF
    result = subprocess.run(
        ["vhs", str(tape_file)], capture_output=True, text=True
    )

    assert result.returncode == 0, f"VHS failed:\n{result.stderr}"
    assert output_gif.exists()

    print(f"CLI demo recorded to {output_gif}")
