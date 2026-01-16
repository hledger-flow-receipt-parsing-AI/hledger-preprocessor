"""TUI navigation utilities using pexpect."""

import sys
import time
from typing import Optional

import pexpect


class Keys:
    """Key escape sequences for terminal input."""

    ENTER = "\r"
    TAB = "\t"
    SPACE = " "
    ESCAPE = "\x1b"

    # Arrow keys
    UP = "\x1b[A"
    DOWN = "\x1b[B"
    RIGHT = "\x1b[C"
    LEFT = "\x1b[D"

    # Other navigation
    HOME = "\x1b[H"
    END = "\x1b[4~"
    PAGE_UP = "\x1b[5~"
    PAGE_DOWN = "\x1b[6~"

    # Editing
    BACKSPACE = "\x7f"
    DELETE = "\x1b[3~"

    # Shift combinations
    SHIFT_TAB = "\x1b[Z"


class TuiNavigator:
    """Helper class for navigating TUI applications via pexpect."""

    def __init__(
        self,
        command: str,
        dimensions: tuple = (32, 120),
        timeout: int = 60,
        log_to_stdout: bool = True,
    ):
        """
        Initialize the TUI navigator.

        Args:
            command: Shell command to spawn
            dimensions: Terminal dimensions (rows, cols)
            timeout: Default timeout for expect operations
            log_to_stdout: Whether to log child output to stdout
        """
        self.command = command
        self.dimensions = dimensions
        self.timeout = timeout
        self.child: Optional[pexpect.spawn] = None
        self.log_to_stdout = log_to_stdout

    def spawn(self) -> "TuiNavigator":
        """Spawn the child process."""
        self.child = pexpect.spawn(
            self.command,
            encoding="utf-8",
            timeout=self.timeout,
            dimensions=self.dimensions,
        )
        if self.log_to_stdout:
            self.child.logfile = sys.stdout
        return self

    def wait_for(
        self, pattern: str, timeout: Optional[int] = None, silent: bool = False
    ) -> bool:
        """
        Wait for a pattern to appear in the output.

        Args:
            pattern: Text pattern to wait for
            timeout: Override default timeout
            silent: Don't raise on timeout, just return False

        Returns:
            True if pattern found, False if timeout (when silent=True)
        """
        if self.child is None:
            raise RuntimeError("Child process not spawned. Call spawn() first.")

        try:
            self.child.expect(pattern, timeout=timeout or self.timeout)
            return True
        except pexpect.TIMEOUT:
            if silent:
                return False
            raise

    def send(self, text: str, pause: float = 0.1) -> "TuiNavigator":
        """
        Send text to the child process.

        Args:
            text: Text or key sequence to send
            pause: Time to wait after sending

        Returns:
            self for chaining
        """
        if self.child is None:
            raise RuntimeError("Child process not spawned. Call spawn() first.")

        self.child.send(text)
        if pause > 0:
            time.sleep(pause)
        return self

    def send_key(self, key: str, pause: float = 0.1) -> "TuiNavigator":
        """Send a single key (alias for send)."""
        return self.send(key, pause)

    def send_keys(self, keys: list, pause: float = 0.05) -> "TuiNavigator":
        """Send multiple keys in sequence."""
        for key in keys:
            self.send(key, pause)
        return self

    def type_text(
        self, text: str, char_pause: float = 0.1, flush: bool = True
    ) -> "TuiNavigator":
        """
        Type text character by character (for visible typing in recordings).

        Args:
            text: Text to type
            char_pause: Pause between characters
            flush: Whether to flush output buffer after each character
        """
        for char in text:
            self.send(char, char_pause)
            if flush:
                self.flush_output()
        return self

    def press_down(self, times: int = 1, pause: float = 0.05) -> "TuiNavigator":
        """Press down arrow key multiple times."""
        for _ in range(times):
            self.send(Keys.DOWN, pause)
            self.flush_output()
        return self

    def press_up(self, times: int = 1, pause: float = 0.05) -> "TuiNavigator":
        """Press up arrow key multiple times."""
        for _ in range(times):
            self.send(Keys.UP, pause)
            self.flush_output()
        return self

    def press_enter(self, pause: float = 0.1) -> "TuiNavigator":
        """Press Enter key."""
        return self.send(Keys.ENTER, pause)

    def press_space(self, pause: float = 0.1) -> "TuiNavigator":
        """Press Space key."""
        return self.send(Keys.SPACE, pause)

    def press_tab(self, pause: float = 0.1) -> "TuiNavigator":
        """Press Tab key."""
        return self.send(Keys.TAB, pause)

    def press_backspace(self, times: int = 1, pause: float = 0.1) -> "TuiNavigator":
        """Press Backspace key multiple times."""
        for _ in range(times):
            self.send(Keys.BACKSPACE, pause)
            self.flush_output()
        return self

    def flush_output(self, timeout: float = 0.1) -> "TuiNavigator":
        """Read and discard any pending output (helps with PTY buffer)."""
        if self.child is None:
            return self

        try:
            self.child.read_nonblocking(size=10000, timeout=timeout)
        except (pexpect.TIMEOUT, pexpect.EOF):
            pass
        return self

    def wait_for_exit(self, timeout: int = 30) -> bool:
        """
        Wait for the child process to exit.

        Returns:
            True if process exited, False if timeout
        """
        if self.child is None:
            return True

        try:
            self.child.expect(pexpect.EOF, timeout=timeout)
            return True
        except pexpect.TIMEOUT:
            return False

    def terminate(self) -> None:
        """Terminate the child process."""
        if self.child is not None:
            self.child.terminate()

    def __enter__(self) -> "TuiNavigator":
        """Context manager entry."""
        return self.spawn()

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit - ensure process is terminated."""
        if self.child is not None and self.child.isalive():
            self.child.terminate()
