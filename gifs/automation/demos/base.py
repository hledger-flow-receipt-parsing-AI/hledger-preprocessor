"""Base class for GIF demo automation."""

import time
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from ..core import Colors, Screen, get_labels_dir, load_config_yaml
from ..navigation import TuiNavigator


class BaseDemo(ABC):
    """Abstract base class for GIF demo automation.

    Subclasses implement specific demo workflows (receipt editing, matching, etc.)
    while inheriting common setup, teardown, and display logic.
    """

    def __init__(
        self,
        config_path: str,
        rows: int = 50,
        cols: int = 120,
        show_keys: bool = True,
    ) -> None:
        """Initialize the demo.

        Args:
            config_path: Path to the YAML config file
            rows: Terminal rows
            cols: Terminal columns
            show_keys: Whether to show key overlay
        """
        self.config_path = config_path
        self.rows = rows
        self.cols = cols
        self.show_keys = show_keys

        self.config_data: Dict[str, Any] = {}
        self.labels_dir: str = ""
        self.navigator: Optional[TuiNavigator] = None

    def setup(self) -> None:
        """Setup the demo environment."""
        self.config_data = load_config_yaml(self.config_path)
        self.labels_dir = get_labels_dir(self.config_data)

    def teardown(self) -> None:
        """Cleanup after the demo."""
        if self.navigator:
            self.navigator.close()
            self.navigator = None

    def show_before_state(self, title: str, data: Dict[str, Any]) -> None:
        """Display the state before the demo action.

        Args:
            title: Title to display
            data: Data to show
        """
        print()
        Screen.print_separator(color=Colors.CYAN)
        print(f"{Colors.BOLD}{title}{Colors.RESET}")
        Screen.print_separator(color=Colors.CYAN)
        self._print_data_summary(data)
        print()

    def show_after_state(self, title: str, data: Dict[str, Any]) -> None:
        """Display the state after the demo action.

        Args:
            title: Title to display
            data: Data to show
        """
        print()
        Screen.print_separator(color=Colors.GREEN)
        print(f"{Colors.BOLD_GREEN}{title}{Colors.RESET}")
        Screen.print_separator(color=Colors.GREEN)
        self._print_data_summary(data)
        print()

    def _print_data_summary(self, data: Dict[str, Any]) -> None:
        """Print a summary of the data dict. Override for custom formatting."""
        for key, value in data.items():
            if isinstance(value, dict):
                print(f"  {key}:")
                for k, v in value.items():
                    print(f"    {k}: {v}")
            else:
                print(f"  {key}: {value}")

    def show_command(
        self,
        command: str,
        description: str = "",
        pause_before: float = 0.5,
        pause_after: float = 1.0,
    ) -> None:
        """Display a command that will be "executed".

        Args:
            command: The command string to display
            description: Optional description of what the command does
            pause_before: Pause before showing command
            pause_after: Pause after showing command
        """
        time.sleep(pause_before)

        if description:
            print(f"\n{Colors.GRAY}# {description}{Colors.RESET}")

        # Show prompt with command
        prompt = f"{Colors.GREEN}${Colors.RESET}"
        print(f"{prompt} {Colors.BOLD}{command}{Colors.RESET}")

        time.sleep(pause_after)

    def type_slowly(
        self, text: str, delay: float = 0.05, newline: bool = True
    ) -> None:
        """Type text character by character for visual effect.

        Args:
            text: Text to type
            delay: Delay between characters
            newline: Whether to print newline at end
        """
        for char in text:
            print(char, end="", flush=True)
            time.sleep(delay)
        if newline:
            print()

    @abstractmethod
    def run(self) -> None:
        """Run the demo workflow. Must be implemented by subclasses."""

    def execute(self) -> None:
        """Execute the full demo with setup and teardown."""
        try:
            self.setup()
            self.run()
        finally:
            self.teardown()
