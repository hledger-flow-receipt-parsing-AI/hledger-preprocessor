#!/usr/bin/env python3
"""Generate typing animation GIFs for YAML files.

Creates nano-style GIF animations showing character-by-character typing
of YAML file content with syntax highlighting.

Based on nano_example.py approach - uses PIL to render frames directly
instead of asciinema recording.

Usage:
    python -m gifs.automation.yaml_typing_gif --input config.yaml --output config.gif
    python -m gifs.automation.yaml_typing_gif --input categories.yaml --output categories.gif --title "categories.yaml"
"""

import argparse
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from typeguard import typechecked

# ─── Configuration ────────────────────────────────────────────────
FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
FONT_SIZE = 16
CHAR_WIDTH = 10
CHAR_HEIGHT = 20

# Terminal dimensions
DEFAULT_COLS = 80
DEFAULT_ROWS = 24

# Colors - dracula theme inspired
BG_COLOR = (40, 42, 54)  # Dark background
HEADER_BG = (68, 71, 90)  # Slightly lighter for header/footer
CURSOR_COLOR = (80, 250, 123)  # Green cursor

COLORS = {
    "key": (139, 233, 253),  # Cyan for YAML keys
    "string": (241, 250, 140),  # Yellow for strings
    "number": (255, 184, 108),  # Orange for numbers
    "bool": (255, 121, 198),  # Pink for booleans
    "null": (98, 114, 164),  # Gray for null
    "comment": (98, 114, 164),  # Gray for comments
    "default": (248, 248, 242),  # Light text
    "header": (248, 248, 242),  # Header text
}

# Animation timing
FRAME_DURATION = 40  # ms per frame
PAUSE_FRAMES = 40  # Extra frames at end

# ─── Regex patterns for YAML syntax ──────────────────────────────
RE_COMMENT = re.compile(r"#.*$")
RE_KEY = re.compile(r"^(\s*)([A-Za-z0-9_\-]+):")
RE_STRING = re.compile(r'".*?"|\'.*?\'')
RE_NUMBER = re.compile(r"\b\d+(\.\d+)?\b")
RE_BOOL = re.compile(r"\b(true|false)\b", re.IGNORECASE)
RE_NULL = re.compile(r"\b(null|~)\b", re.IGNORECASE)


# ─── Helpers ─────────────────────────────────────────────────────
def load_yaml_lines(filepath: str | Path) -> list[str]:
    """Load YAML file and return lines."""
    with open(filepath, encoding="utf-8") as f:
        return f.read().splitlines(keepends=False)


def wrap_line(line: str, cols: int) -> list[str]:
    """Wrap a line to fit within column width."""
    return [line[i : i + cols] for i in range(0, len(line), cols)] or [""]


def syntax_tokens(line: str) -> list[tuple[int, str, tuple[int, int, int]]]:
    """Parse line into syntax-highlighted tokens.

    Returns list of (start_idx, text, color) tuples.
    """
    tokens = []
    idx = 0

    def emit(text: str, color: tuple[int, int, int]) -> None:
        nonlocal idx
        tokens.append((idx, text, color))
        idx += len(text)

    # Handle comments first
    m = RE_COMMENT.search(line)
    if m:
        code = line[: m.start()]
        comment = line[m.start() :]
    else:
        code = line
        comment = None

    pos = 0
    while pos < len(code):
        matched = False
        for regex, color_name in [
            (RE_KEY, "key"),
            (RE_STRING, "string"),
            (RE_NUMBER, "number"),
            (RE_BOOL, "bool"),
            (RE_NULL, "null"),
        ]:
            m = regex.match(code[pos:])
            if m:
                emit(m.group(0), COLORS[color_name])
                pos += len(m.group(0))
                matched = True
                break
        if not matched:
            emit(code[pos], COLORS["default"])
            pos += 1

    if comment:
        emit(comment, COLORS["comment"])

    return tokens


@typechecked
def get_wrapped_lines_up_to(
    lines: list[str], up_to_line_idx: int, up_to_char_idx: int, cols: int
) -> list[tuple[str, bool]]:
    """Get screen lines up to a specific position.

    Returns list of (text, is_comment) pairs for rendering.
    """
    screen_lines = []
    for i, line in enumerate(lines):
        comment_match = RE_COMMENT.search(line)
        comment_start = comment_match.start() if comment_match else -1

        current_text = line if i < up_to_line_idx else line[:up_to_char_idx]

        for segment in wrap_line(current_text, cols):
            start_pos_in_line = current_text.find(segment)
            is_comment = (
                comment_start != -1 and start_pos_in_line >= comment_start
            )
            screen_lines.append((segment, is_comment))

        if i == up_to_line_idx:
            break
    return screen_lines


def draw_header(
    draw: ImageDraw.ImageDraw,
    title: str,
    cols: int,
    font: ImageFont.FreeTypeFont,
) -> None:
    """Draw nano-style header bar."""
    header_text = f"  GNU nano 7.2      {title}"
    header_text = header_text.ljust(cols)

    # Draw header background
    draw.rectangle((0, 0, cols * CHAR_WIDTH, CHAR_HEIGHT), fill=HEADER_BG)
    draw.text((0, 0), header_text, font=font, fill=COLORS["header"])


def draw_footer(
    draw: ImageDraw.ImageDraw,
    rows: int,
    cols: int,
    font: ImageFont.FreeTypeFont,
) -> None:
    """Draw nano-style footer with key bindings."""
    footer_y = (rows - 2) * CHAR_HEIGHT

    line1 = "^G Help    ^O Write Out  ^W Where Is   ^K Cut"
    line2 = "^X Exit    ^R Read File  ^\\ Replace    ^U Paste"

    line1 = line1.ljust(cols)
    line2 = line2.ljust(cols)

    # Draw footer backgrounds
    draw.rectangle(
        (0, footer_y, cols * CHAR_WIDTH, footer_y + CHAR_HEIGHT),
        fill=HEADER_BG,
    )
    draw.rectangle(
        (
            0,
            footer_y + CHAR_HEIGHT,
            cols * CHAR_WIDTH,
            footer_y + 2 * CHAR_HEIGHT,
        ),
        fill=HEADER_BG,
    )

    draw.text((0, footer_y), line1, font=font, fill=COLORS["header"])
    draw.text(
        (0, footer_y + CHAR_HEIGHT), line2, font=font, fill=COLORS["header"]
    )


@typechecked
def create_frame(
    screen_lines: list[tuple[str, bool]],
    cursor_screen_row: int,
    cursor_col_in_row: int,
    scroll_offset: int,
    font: ImageFont.FreeTypeFont,
    title: str,
    rows: int,
    cols: int,
) -> Image.Image:
    """Create a single frame of the animation."""
    img = Image.new("RGB", (cols * CHAR_WIDTH, rows * CHAR_HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img)

    # Draw header
    draw_header(draw, title, cols, font)

    # Draw content area (rows 1 to rows-3, leaving room for header and 2 footer lines)
    content_rows = rows - 3
    y = CHAR_HEIGHT  # Start after header

    for row_pair in screen_lines[scroll_offset : scroll_offset + content_rows]:
        line_text, is_comment_wrap = row_pair
        x = 0

        if is_comment_wrap:
            draw.text((x, y), line_text, font=font, fill=COLORS["comment"])
        else:
            for _, text, color in syntax_tokens(line_text):
                draw.text((x, y), text, font=font, fill=color)
                x += len(text) * CHAR_WIDTH
        y += CHAR_HEIGHT

    # Draw cursor
    cursor_visible_row = cursor_screen_row - scroll_offset
    if 0 <= cursor_visible_row < content_rows:
        cx = cursor_col_in_row * CHAR_WIDTH
        cy = (cursor_visible_row + 1) * CHAR_HEIGHT  # +1 for header
        draw.rectangle(
            (cx, cy, cx + CHAR_WIDTH - 1, cy + CHAR_HEIGHT - 1),
            fill=CURSOR_COLOR,
        )

    # Draw footer
    draw_footer(draw, rows, cols, font)

    return img


def make_typing_gif(
    input_file: str | Path,
    output_file: str | Path,
    title: str | None = None,
    rows: int = DEFAULT_ROWS,
    cols: int = DEFAULT_COLS,
) -> None:
    """Generate a typing animation GIF for a YAML file.

    Args:
        input_file: Path to the YAML file to animate
        output_file: Path for the output GIF
        title: Title to show in header (defaults to filename)
        rows: Terminal height in rows
        cols: Terminal width in columns
    """
    input_path = Path(input_file)
    output_path = Path(output_file)

    if title is None:
        title = input_path.name

    lines = load_yaml_lines(input_path)

    try:
        font = ImageFont.truetype(FONT_PATH, FONT_SIZE)
    except OSError:
        font = ImageFont.load_default()

    frames = []
    scroll_offset = 0
    content_rows = rows - 3  # Header + 2 footer lines

    for line_idx, full_line in enumerate(lines):
        char_idx = 0
        while char_idx <= len(full_line):
            screen_lines = get_wrapped_lines_up_to(
                lines, line_idx, char_idx, cols
            )

            cursor_screen_row = len(screen_lines) - 1
            last_wrapped = wrap_line(full_line[:char_idx], cols)
            cursor_col_in_row = len(last_wrapped[-1])

            img = create_frame(
                screen_lines,
                cursor_screen_row,
                cursor_col_in_row,
                scroll_offset,
                font,
                title,
                rows,
                cols,
            )
            frames.append(img)
            char_idx += 1

        # Handle scrolling
        current_height = len(
            get_wrapped_lines_up_to(lines, line_idx, len(full_line), cols)
        )
        while current_height - scroll_offset > content_rows - 2:
            scroll_offset += 1
            wrapped = wrap_line(full_line, cols)
            for _ in range(3):  # Extra frames for smooth scroll
                frames.append(
                    create_frame(
                        get_wrapped_lines_up_to(
                            lines, line_idx, len(full_line), cols
                        ),
                        current_height - 1,
                        len(wrapped[-1]),
                        scroll_offset,
                        font,
                        title,
                        rows,
                        cols,
                    )
                )

    # Add pause at end
    if frames:
        for _ in range(PAUSE_FRAMES):
            frames.append(frames[-1])

        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        frames[0].save(
            output_path,
            save_all=True,
            append_images=frames[1:],
            duration=FRAME_DURATION,
            loop=0,
            optimize=False,
        )
        print(f"Generated: {output_path}")


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Generate typing animation GIF for YAML files"
    )
    parser.add_argument(
        "--input", "-i", required=True, help="Input YAML file path"
    )
    parser.add_argument(
        "--output", "-o", required=True, help="Output GIF file path"
    )
    parser.add_argument(
        "--title",
        "-t",
        help="Title to display in header (defaults to filename)",
    )
    parser.add_argument(
        "--rows", "-r", type=int, default=DEFAULT_ROWS, help="Terminal rows"
    )
    parser.add_argument(
        "--cols", "-c", type=int, default=DEFAULT_COLS, help="Terminal columns"
    )

    args = parser.parse_args()

    if not Path(args.input).exists():
        print(f"Error: Input file not found: {args.input}")
        exit(1)

    make_typing_gif(
        input_file=args.input,
        output_file=args.output,
        title=args.title,
        rows=args.rows,
        cols=args.cols,
    )


if __name__ == "__main__":
    main()
