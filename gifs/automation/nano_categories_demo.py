#!/usr/bin/env python3
"""Record a GIF of typing categories.yaml from scratch in nano."""

import os
import pty
import select
import time

import pyte
from PIL import Image, ImageDraw, ImageFont

# Terminal dimensions - wider to avoid line wrapping
COLS, ROWS = 80, 30
FONT_SIZE = 14
CHAR_WIDTH = 9
CHAR_HEIGHT = 16


def get_font():
    """Try to get a monospace font."""
    for font_name in [
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "/usr/share/fonts/TTF/DejaVuSansMono.ttf",
        "/System/Library/Fonts/Menlo.ttc",
        "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
    ]:
        if os.path.exists(font_name):
            return ImageFont.truetype(font_name, FONT_SIZE)
    return ImageFont.load_default()


def render_screen(screen, font):
    """Render pyte screen to PIL Image."""
    width = COLS * CHAR_WIDTH
    height = ROWS * CHAR_HEIGHT
    img = Image.new("RGB", (width, height), "black")
    draw = ImageDraw.Draw(img)

    for y in range(ROWS):
        for x in range(COLS):
            char = screen.buffer[y][x]
            ch = char.data if char.data else " "
            if char.reverse:
                draw.rectangle(
                    [
                        x * CHAR_WIDTH,
                        y * CHAR_HEIGHT,
                        (x + 1) * CHAR_WIDTH,
                        (y + 1) * CHAR_HEIGHT,
                    ],
                    fill="white",
                )
                draw.text(
                    (x * CHAR_WIDTH, y * CHAR_HEIGHT),
                    ch,
                    font=font,
                    fill="black",
                )
            else:
                draw.text(
                    (x * CHAR_WIDTH, y * CHAR_HEIGHT),
                    ch,
                    font=font,
                    fill="white",
                )

    # Draw cursor
    cx, cy = screen.cursor.x, screen.cursor.y
    if 0 <= cx < COLS and 0 <= cy < ROWS:
        draw.rectangle(
            [
                cx * CHAR_WIDTH,
                cy * CHAR_HEIGHT,
                (cx + 1) * CHAR_WIDTH,
                (cy + 1) * CHAR_HEIGHT,
            ],
            outline="lime",
        )
    return img


class NanoRecorder:
    """Records nano editing session to GIF."""

    def __init__(self, filename: str, output_gif: str):
        self.filename = filename
        self.output_gif = output_gif
        self.screen = pyte.Screen(COLS, ROWS)
        self.stream = pyte.Stream(self.screen)
        self.font = get_font()
        self.frames = []
        self.master_fd = None
        self.pid = None

    def start_nano(self):
        """Start nano in a pseudo-terminal."""
        self.master_fd, slave_fd = pty.openpty()

        import fcntl
        import struct
        import termios

        winsize = struct.pack("HHHH", ROWS, COLS, 0, 0)
        fcntl.ioctl(slave_fd, termios.TIOCSWINSZ, winsize)

        self.pid = os.fork()
        if self.pid == 0:
            os.close(self.master_fd)
            os.setsid()
            os.dup2(slave_fd, 0)
            os.dup2(slave_fd, 1)
            os.dup2(slave_fd, 2)
            os.close(slave_fd)
            os.environ["TERM"] = "xterm-256color"
            os.execlp("nano", "nano", self.filename)

        os.close(slave_fd)

    def read_output(self, timeout: float = 0.1):
        """Read and process terminal output."""
        end_time = time.time() + timeout
        while time.time() < end_time:
            r, _, _ = select.select([self.master_fd], [], [], 0.02)
            if r:
                try:
                    data = os.read(self.master_fd, 8192)
                    if data:
                        self.stream.feed(data.decode("utf-8", errors="replace"))
                except OSError:
                    break

    def capture_frame(self):
        """Capture current screen as frame."""
        self.frames.append(render_screen(self.screen, self.font))

    def type_char(self, char: str, delay: float = 0.03):
        """Type a single character."""
        os.write(self.master_fd, char.encode())
        time.sleep(delay)
        self.read_output(0.02)
        self.capture_frame()

    def type_text(self, text: str, delay: float = 0.03):
        """Type text character by character."""
        for char in text:
            self.type_char(char, delay)

    def type_line(self, text: str, delay: float = 0.03):
        """Type a line and press enter."""
        self.type_text(text, delay)
        self.type_char("\n", delay=0.05)

    def send_control(self, char: str, delay: float = 0.3):
        """Send control character."""
        ctrl_char = chr(ord(char.upper()) - 64)
        os.write(self.master_fd, ctrl_char.encode())
        time.sleep(delay)
        self.read_output(0.2)
        self.capture_frame()

    def wait_and_capture(self, duration: float = 0.5, frames: int = 3):
        """Wait and capture multiple frames."""
        for _ in range(frames):
            time.sleep(duration / frames)
            self.read_output(0.05)
            self.capture_frame()

    def cleanup(self):
        """Clean up process."""
        if self.master_fd:
            os.close(self.master_fd)
        if self.pid:
            try:
                os.waitpid(self.pid, 0)
            except ChildProcessError:
                pass

    def save_gif(self, duration: int = 100):
        """Save frames as GIF."""
        if self.frames:
            self.frames[0].save(
                self.output_gif,
                save_all=True,
                append_images=self.frames[1:],
                duration=duration,
                loop=0,
            )
            print(f"Saved {self.output_gif} with {len(self.frames)} frames")


def main():
    """Main entry point."""
    # Setup - create empty file
    demo_dir = "/tmp/hledger_demo"
    os.makedirs(demo_dir, exist_ok=True)
    categories_file = os.path.join(demo_dir, "categories.yaml")

    # Start with empty file
    open(categories_file, "w").close()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(script_dir, "..", "02_add_category", "output")
    os.makedirs(output_dir, exist_ok=True)
    output_gif = os.path.join(output_dir, "02_add_category.gif")

    recorder = NanoRecorder(categories_file, output_gif)

    # Typing speed
    d = 0.025  # delay per character

    try:
        recorder.start_nano()

        # Wait for nano to start
        time.sleep(0.6)
        recorder.read_output(0.3)
        recorder.capture_frame()
        recorder.wait_and_capture(0.8, 4)

        # Type the entire categories file from scratch
        # Subscriptions
        recorder.type_line("abonnement:", delay=d)
        recorder.type_line("  monthly:", delay=d)
        recorder.type_line("    phone: {}", delay=d)
        recorder.type_line("    rent: {}", delay=d)
        recorder.type_line("", delay=d)

        # Groceries
        recorder.type_line("groceries:", delay=d)
        recorder.type_line("  supermarket: {}", delay=d)
        recorder.type_line("  farmers_market: {}", delay=d)
        recorder.type_line("", delay=d)

        # Transport
        recorder.type_line("transport:", delay=d)
        recorder.type_line("  public_transit: {}", delay=d)
        recorder.type_line("  taxi: {}", delay=d)
        recorder.type_line("  fuel: {}", delay=d)
        recorder.type_line("", delay=d)

        # Dining
        recorder.type_line("dining:", delay=d)
        recorder.type_line("  restaurants: {}", delay=d)
        recorder.type_line("  Brocoli: {}", delay=d)
        recorder.type_line("  delivery: {}", delay=d)
        recorder.type_line("", delay=d)

        # Utilities
        recorder.type_line("utilities:", delay=d)
        recorder.type_line("  electricity: {}", delay=d)
        recorder.type_line("  water: {}", delay=d)
        recorder.type_line("  internet: {}", delay=d)
        recorder.type_line("", delay=d)

        # Wallet
        recorder.type_line("wallet:", delay=d)
        recorder.type_line("  physical: {}", delay=d)
        recorder.type_line("", delay=d)

        # Withdrawal
        recorder.type_line("withdrawl:", delay=d)
        recorder.type_line("  euro:", delay=d)
        recorder.type_text("    pound: {}", delay=d)

        recorder.wait_and_capture(1.5, 8)

        # Save: Ctrl+O
        recorder.send_control("o", delay=0.4)
        recorder.wait_and_capture(0.3, 2)

        # Confirm filename with Enter
        recorder.type_char("\n", delay=0.3)
        recorder.wait_and_capture(0.8, 4)

        # Exit: Ctrl+X
        recorder.send_control("x", delay=0.3)
        recorder.wait_and_capture(0.5, 3)

    finally:
        recorder.cleanup()

    recorder.save_gif(duration=60)


if __name__ == "__main__":
    main()
