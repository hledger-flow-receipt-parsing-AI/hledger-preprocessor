"""Theme registry for GIF generation with agg."""

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class Theme:
    """A terminal color theme for GIF generation.

    Attributes:
        name: Theme identifier used in filename (e.g., "dracula")
        value: Theme value for agg - either a builtin name or custom hex colors
        description: Optional human-readable description
    """

    name: str
    value: str
    description: str = ""

    def is_builtin(self) -> bool:
        """Check if this is a builtin agg theme."""
        # Builtin themes don't contain commas (hex values are comma-separated)
        return "," not in self.value


# Built-in agg themes
BUILTIN_THEMES: List[Theme] = [
    Theme("dracula", "dracula", "Dark purple theme"),
    Theme("monokai", "monokai", "Monokai color scheme"),
    Theme("solarized-dark", "solarized-dark", "Solarized dark variant"),
    Theme("solarized-light", "solarized-light", "Solarized light variant"),
]

# Custom retro themes (format: bg,fg,black,red,green,yellow,blue,magenta,cyan,white)
RETRO_THEMES: List[Theme] = [
    Theme(
        "amber",
        "0a0a0a,ffb000,1a1a1a,cc4400,ff8800,ffb000,ff6600,cc6600,ffcc00,ffdd88",
        "Classic amber phosphor terminal",
    ),
    Theme(
        "green-phosphor",
        "0a0a0a,33ff33,1a1a1a,00cc00,33ff33,66ff66,00aa00,009900,99ff99,ccffcc",
        "Classic green phosphor terminal",
    ),
    Theme(
        "cyan-cool",
        "0a0f14,00ffff,0a1a1f,ff6666,66ffcc,ffff66,6699ff,ff66ff,00ffff,ffffff",
        "Cool cyan retro futuristic",
    ),
    Theme(
        "matrix",
        "000000,00ff00,0a0a0a,ff0000,00ff00,ffff00,0066ff,ff00ff,00ffff,ffffff",
        "Matrix-inspired green on black",
    ),
]

# All themes combined
ALL_THEMES: List[Theme] = BUILTIN_THEMES + RETRO_THEMES


class ThemeRegistry:
    """Registry for managing and accessing themes."""

    def __init__(self, themes: Optional[List[Theme]] = None) -> None:
        """Initialize with a list of themes, defaults to ALL_THEMES."""
        self._themes: Dict[str, Theme] = {}
        for theme in themes or ALL_THEMES:
            self.register(theme)

    def register(self, theme: Theme) -> None:
        """Register a theme in the registry."""
        self._themes[theme.name] = theme

    def get(self, name: str) -> Optional[Theme]:
        """Get a theme by name."""
        return self._themes.get(name)

    def get_all(self) -> List[Theme]:
        """Get all registered themes."""
        return list(self._themes.values())

    def get_names(self) -> List[str]:
        """Get all theme names."""
        return list(self._themes.keys())

    def to_bash_array(self) -> str:
        """Generate a bash array definition for use in shell scripts.

        Returns:
            A string like:
            declare -a THEMES=(
                "dracula:dracula"
                "amber:0a0a0a,ffb000,..."
            )
        """
        lines = ["declare -a THEMES=("]
        for theme in self._themes.values():
            lines.append(f'    "{theme.name}:{theme.value}"')
        lines.append(")")
        return "\n".join(lines)
