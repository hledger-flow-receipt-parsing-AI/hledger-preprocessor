#!/usr/bin/env python3
"""Generate userstories.md from userstory_dag_data.yaml.

Reads the single-source YAML and produces a Markdown document matching
the format of userstories_v0.md.

Usage:
    python generate_userstories_md.py                # write to ../userstories.md
    python generate_userstories_md.py -o FILE        # write to FILE
    python generate_userstories_md.py --stdout        # print to stdout
"""

import argparse
import sys
from collections import OrderedDict
from pathlib import Path

import yaml

SCRIPT_DIR = Path(__file__).parent
DATA_FILE = SCRIPT_DIR / "userstory_dag_data.yaml"
DEFAULT_OUTPUT = SCRIPT_DIR.parent.parent / "userstories.md"

PREAMBLE = """\
# User Stories — hledger-preprocessor

This document contains detailed user stories for the hledger-preprocessor
ecosystem. Each story follows the format:

> **As a** [persona], **I want to** [action], **so that** [benefit].

Stories are organised by the 5-step workflow shown in the README, followed by
cross-cutting concerns. Stories marked *[NOT YET IMPLEMENTED]* describe
functionality that does not yet exist in the codebase.

*This file is auto-generated from `user_stories/dag/userstory_dag_data.yaml`.*
*Edit the YAML, then run `python user_stories/dag/generate_userstories_md.py`.*
"""


def load_data():
    with open(DATA_FILE) as f:
        return yaml.safe_load(f)


def render_story(s: dict) -> str:
    """Render one story as Markdown."""
    lines = []

    # Heading
    status = s.get("status")
    title = s.get("title", s.get("label", s["id"]))
    if status:
        lines.append(f"### {s['id']} — {title} *[{status}]*")
    else:
        lines.append(f"### {s['id']} — {title}")
    lines.append("")

    # As a / I want / so that
    as_a = s.get("as_a", "")
    i_want = s.get("i_want", "")
    so_that = s.get("so_that", "")
    if as_a:
        lines.append(f"**As a** {as_a},")
        lines.append(f"**I want to** {i_want},")
        lines.append(f"**so that** {so_that}")
        lines.append("")

    # Resolution / Workaround (US-3.12)
    if "resolution" in s:
        lines.append(f"**Resolution:** {s['resolution']}")
        lines.append("")
    if "workaround" in s:
        lines.append(f"**Workaround:** {s['workaround']}")
        lines.append("")

    # Design note (US-4.4)
    if "design_note" in s:
        lines.append(f"**Design note:** {s['design_note']}")
        lines.append("")

    # Acceptance criteria
    criteria = s.get("acceptance_criteria", [])
    if criteria:
        lines.append("**Acceptance criteria:**")
        lines.append("")
        for c in criteria:
            lines.append(f"- {c}")
        lines.append("")

    return "\n".join(lines)


def generate_markdown(data: dict) -> str:
    """Generate the full Markdown document."""
    stories = data["stories"]

    # Group by section, preserving order
    sections = OrderedDict()
    for s in stories:
        sec = s.get("section", "Other")
        if sec not in sections:
            sections[sec] = []
        sections[sec].append(s)

    parts = [PREAMBLE, "---", ""]
    for section, story_list in sections.items():
        parts.append(f"## {section}")
        parts.append("")
        for s in story_list:
            parts.append(render_story(s))
            parts.append("---")
            parts.append("")

    return "\n".join(parts)


def main():
    parser = argparse.ArgumentParser(
        description="Generate userstories.md from YAML data."
    )
    parser.add_argument(
        "-o", "--output", type=str, default=None,
        help=f"Output file (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--stdout", action="store_true",
        help="Print to stdout instead of writing a file",
    )
    args = parser.parse_args()

    data = load_data()
    md = generate_markdown(data)

    if args.stdout:
        print(md)
    else:
        outpath = Path(args.output) if args.output else DEFAULT_OUTPUT
        outpath.write_text(md, encoding="utf-8")
        print(f"Written: {outpath}")


if __name__ == "__main__":
    main()
