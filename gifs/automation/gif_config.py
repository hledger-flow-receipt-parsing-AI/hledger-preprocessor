#!/usr/bin/env python3
"""GIF generation configuration loader.

This module provides utilities for loading and querying the gif_config.yaml file.
It can be used both as a library and as a CLI tool for bash scripts.
"""

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import yaml


@dataclass
class TerminalConfig:
    """Terminal dimension configuration."""

    rows: int = 50
    cols: int = 120


@dataclass
class RenderingConfig:
    """Rendering settings for GIF generation."""

    font_size: int = 20
    line_height: float = 1.2
    terminal: TerminalConfig = field(default_factory=TerminalConfig)
    idle_time_limit: int = 2


@dataclass
class ThemeConfig:
    """Theme configuration."""

    generate_themed_gifs: bool = True
    generate_showcase: bool = True
    default_theme: str = "dracula"
    available: Dict[str, str] = field(default_factory=dict)
    enabled: List[str] = field(default_factory=list)


@dataclass
class DemoConfig:
    """Configuration for a single demo."""

    enabled: bool = True
    terminal: Optional[TerminalConfig] = None


@dataclass
class OutputConfig:
    """Output settings."""

    optimize: bool = True
    clean_before_generate: bool = True


@dataclass
class GifConfig:
    """Complete GIF generation configuration."""

    rendering: RenderingConfig
    themes: ThemeConfig
    demos: Dict[str, DemoConfig]
    output: OutputConfig

    def get_enabled_themes(self) -> List[tuple]:
        """Get list of enabled themes as (name, value) tuples."""
        if not self.themes.enabled:
            # If no enabled list, use all available
            return list(self.themes.available.items())

        return [
            (name, self.themes.available[name])
            for name in self.themes.enabled
            if name in self.themes.available
        ]

    def get_demo_terminal(self, demo_name: str) -> TerminalConfig:
        """Get terminal config for a demo, with fallback to global settings."""
        demo = self.demos.get(demo_name)
        if demo and demo.terminal:
            return demo.terminal
        return self.rendering.terminal

    def is_demo_enabled(self, demo_name: str) -> bool:
        """Check if a demo is enabled."""
        demo = self.demos.get(demo_name)
        if demo is None:
            # Unknown demos are enabled by default
            return True
        return demo.enabled


def load_config(config_path: Optional[str] = None) -> GifConfig:
    """Load GIF configuration from YAML file.

    Args:
        config_path: Path to config file. If None, looks for gif_config.yaml
                     in the gifs/ directory.

    Returns:
        GifConfig object with all settings.
    """
    if config_path is None:
        # Find config relative to this file
        gifs_dir = Path(__file__).parent.parent
        config_path = gifs_dir / "gif_config.yaml"

    with open(config_path) as f:
        data = yaml.safe_load(f)

    # Parse rendering config
    rendering_data = data.get("rendering", {})
    terminal_data = rendering_data.get("terminal", {})
    rendering = RenderingConfig(
        font_size=rendering_data.get("font_size", 20),
        line_height=rendering_data.get("line_height", 1.2),
        terminal=TerminalConfig(
            rows=terminal_data.get("rows", 50),
            cols=terminal_data.get("cols", 120),
        ),
        idle_time_limit=rendering_data.get("idle_time_limit", 2),
    )

    # Parse themes config
    themes_data = data.get("themes", {})
    themes = ThemeConfig(
        generate_themed_gifs=themes_data.get("generate_themed_gifs", True),
        generate_showcase=themes_data.get("generate_showcase", True),
        default_theme=themes_data.get("default_theme", "dracula"),
        available=themes_data.get("available", {}),
        enabled=themes_data.get("enabled", []),
    )

    # Parse demos config
    demos_data = data.get("demos", {})
    demos = {}
    for demo_name, demo_data in demos_data.items():
        if demo_data is None:
            demo_data = {}
        terminal = None
        if "terminal" in demo_data:
            t = demo_data["terminal"]
            terminal = TerminalConfig(
                rows=t.get("rows", rendering.terminal.rows),
                cols=t.get("cols", rendering.terminal.cols),
            )
        demos[demo_name] = DemoConfig(
            enabled=demo_data.get("enabled", True),
            terminal=terminal,
        )

    # Parse output config
    output_data = data.get("output", {})
    output = OutputConfig(
        optimize=output_data.get("optimize", True),
        clean_before_generate=output_data.get("clean_before_generate", True),
    )

    return GifConfig(
        rendering=rendering,
        themes=themes,
        demos=demos,
        output=output,
    )


def get_bash_themes_array(config: GifConfig) -> str:
    """Generate bash array declaration for themes.

    Returns a string like:
    ("dracula:dracula" "monokai:monokai" ...)
    """
    themes = config.get_enabled_themes()
    entries = [f'"{name}:{value}"' for name, value in themes]
    return "(" + " ".join(entries) + ")"


def main():
    """CLI interface for querying config from bash scripts."""
    parser = argparse.ArgumentParser(
        description="Query GIF generation configuration"
    )
    parser.add_argument(
        "--config",
        "-c",
        help="Path to gif_config.yaml",
    )
    parser.add_argument(
        "query",
        nargs="?",
        help=(
            "Config query (e.g., 'rendering.font_size', 'themes.enabled', "
            "'demo.start_sh_pipeline.enabled')"
        ),
    )
    parser.add_argument(
        "--themes-array",
        action="store_true",
        help="Output themes as bash array declaration",
    )
    parser.add_argument(
        "--demo-enabled",
        metavar="DEMO",
        help="Check if a demo is enabled (returns 'true' or 'false')",
    )
    parser.add_argument(
        "--demo-rows",
        metavar="DEMO",
        help="Get terminal rows for a demo",
    )
    parser.add_argument(
        "--demo-cols",
        metavar="DEMO",
        help="Get terminal cols for a demo",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output full config as JSON",
    )

    args = parser.parse_args()

    try:
        config = load_config(args.config)
    except FileNotFoundError:
        print("Error: gif_config.yaml not found", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error loading config: {e}", file=sys.stderr)
        sys.exit(1)

    # Handle specific queries
    if args.themes_array:
        print(get_bash_themes_array(config))
        return

    if args.demo_enabled:
        print("true" if config.is_demo_enabled(args.demo_enabled) else "false")
        return

    if args.demo_rows:
        terminal = config.get_demo_terminal(args.demo_rows)
        print(terminal.rows)
        return

    if args.demo_cols:
        terminal = config.get_demo_terminal(args.demo_cols)
        print(terminal.cols)
        return

    if args.json:
        # Convert to dict for JSON output
        output = {
            "rendering": {
                "font_size": config.rendering.font_size,
                "line_height": config.rendering.line_height,
                "terminal": {
                    "rows": config.rendering.terminal.rows,
                    "cols": config.rendering.terminal.cols,
                },
                "idle_time_limit": config.rendering.idle_time_limit,
            },
            "themes": {
                "generate_themed_gifs": config.themes.generate_themed_gifs,
                "generate_showcase": config.themes.generate_showcase,
                "default_theme": config.themes.default_theme,
                "available": config.themes.available,
                "enabled": config.themes.enabled,
            },
            "demos": {
                name: {
                    "enabled": demo.enabled,
                    "terminal": (
                        {
                            "rows": demo.terminal.rows,
                            "cols": demo.terminal.cols,
                        }
                        if demo.terminal
                        else None
                    ),
                }
                for name, demo in config.demos.items()
            },
            "output": {
                "optimize": config.output.optimize,
                "clean_before_generate": config.output.clean_before_generate,
            },
        }
        print(json.dumps(output, indent=2))
        return

    # Handle dot-notation queries
    if args.query:
        parts = args.query.split(".")
        try:
            if parts[0] == "rendering":
                if len(parts) == 2:
                    if parts[1] == "font_size":
                        print(config.rendering.font_size)
                    elif parts[1] == "line_height":
                        print(config.rendering.line_height)
                    elif parts[1] == "idle_time_limit":
                        print(config.rendering.idle_time_limit)
                elif len(parts) == 3 and parts[1] == "terminal":
                    if parts[2] == "rows":
                        print(config.rendering.terminal.rows)
                    elif parts[2] == "cols":
                        print(config.rendering.terminal.cols)
            elif parts[0] == "themes":
                if len(parts) == 2:
                    if parts[1] == "generate_themed_gifs":
                        print(
                            "true"
                            if config.themes.generate_themed_gifs
                            else "false"
                        )
                    elif parts[1] == "generate_showcase":
                        print(
                            "true"
                            if config.themes.generate_showcase
                            else "false"
                        )
                    elif parts[1] == "default_theme":
                        print(config.themes.default_theme)
                    elif parts[1] == "enabled":
                        print(" ".join(config.themes.enabled))
            elif parts[0] == "output":
                if len(parts) == 2:
                    if parts[1] == "optimize":
                        print("true" if config.output.optimize else "false")
                    elif parts[1] == "clean_before_generate":
                        print(
                            "true"
                            if config.output.clean_before_generate
                            else "false"
                        )
            else:
                print(f"Unknown query: {args.query}", file=sys.stderr)
                sys.exit(1)
        except (IndexError, KeyError, AttributeError) as e:
            print(f"Invalid query: {args.query} ({e})", file=sys.stderr)
            sys.exit(1)
        return

    # Default: print help
    parser.print_help()


if __name__ == "__main__":
    main()
