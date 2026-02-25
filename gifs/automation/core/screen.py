"""Terminal screen manipulation utilities."""

import sys
from pathlib import Path
from typing import List, Optional

from .colors import Colors

# Path to the YAML data file (resolved lazily to avoid import-time I/O)
_DAG_DATA_DIR = Path(__file__).parent.parent.parent.parent / "user_stories" / "dag"


def emit_node_marker(node_id: str) -> None:
    """Emit a machine-readable marker into the terminal stream.

    The marker ``@@NODE:<node_id>@@`` is captured by asciinema in the
    ``.cast`` file with an exact timestamp.  ``generate_site.py`` parses
    these markers to build per-node video timestamps for the interactive
    DAG viewer.

    The marker is printed as dim text so it is nearly invisible in the
    terminal and the resulting GIF, but fully present in the cast data.
    """
    print(f"\x1b[2m@@NODE:{node_id}@@\x1b[0m", flush=True)


class StoryMarkerEmitter:
    """Stateful emitter that walks through a story's YAML-declared marker sequence.

    Demo scripts use this instead of hardcoded ``emit_node_marker()`` calls.
    It guarantees markers appear in the cast file in the exact order
    declared in ``userstory_dag_data.yaml``, which is what
    ``generate_site.py`` expects for video/DAG synchronization.

    Usage::

        emitter = StoryMarkerEmitter("US-3.1")
        emitter.emit_until("start_2024_1000eur")
        # ... do setup ...
        emitter.emit_until("img_ekoplaza_card")
        # ... show receipt image ...
        emitter.emit_until("out_auto_1hit")
        # ... run matching ...
        emitter.emit_remaining()
    """

    def __init__(self, story_id: str, data_file: Optional[Path] = None) -> None:
        # Import story_components lazily to avoid circular dependency
        dag_dir = str(data_file.parent if data_file else _DAG_DATA_DIR)
        if dag_dir not in sys.path:
            sys.path.insert(0, dag_dir)
        from story_components import (
            build_node_index,
            get_marker_sequence,
            get_story_by_id,
            load_dag_data,
        )

        data = load_dag_data(
            data_file=data_file or (_DAG_DATA_DIR / "userstory_dag_data.yaml")
        )
        node_index = build_node_index(data=data)
        story = get_story_by_id(data=data, story_id=story_id)
        if not story:
            raise ValueError(f"Story '{story_id}' not found in YAML")
        self._sequence = get_marker_sequence(story=story, node_index=node_index)
        self._pos = 0

    @property
    def sequence(self) -> List[str]:
        """The full ordered marker sequence for this story."""
        return list(self._sequence)

    def emit_next(self) -> Optional[str]:
        """Emit the next marker in sequence.  Returns the marker ID or None."""
        if self._pos >= len(self._sequence):
            return None
        marker_id = self._sequence[self._pos]
        emit_node_marker(marker_id)
        self._pos += 1
        return marker_id

    def emit_until(self, target_node: str) -> List[str]:
        """Emit markers up to and including *target_node*.

        Matches on the base node ID (ignoring ``__sub_component`` suffixes),
        so ``emit_until("cfg_1b1w")`` will also emit all sub-component
        markers for ``cfg_1b1w``.
        """
        emitted: List[str] = []
        while self._pos < len(self._sequence):
            marker_id = self._sequence[self._pos]
            emit_node_marker(marker_id)
            self._pos += 1
            emitted.append(marker_id)
            # Stop after emitting the last sub-component of target_node,
            # or the target itself if it has no sub-components.
            base_id = marker_id.split("__")[0]
            if base_id == target_node:
                # Peek ahead: if next marker is still a sub-component of
                # the same node, keep going.
                if self._pos < len(self._sequence):
                    next_base = self._sequence[self._pos].split("__")[0]
                    if next_base == target_node:
                        continue
                break
        return emitted

    def emit_remaining(self) -> List[str]:
        """Emit all remaining markers."""
        emitted: List[str] = []
        while self._pos < len(self._sequence):
            marker_id = self.emit_next()
            if marker_id:
                emitted.append(marker_id)
        return emitted


class Screen:
    """Terminal screen manipulation utilities."""

    CLEAR = "\x1b[2J"
    HOME = "\x1b[H"
    CLEAR_AND_HOME = "\x1b[2J\x1b[H"

    @classmethod
    def clear(cls) -> None:
        """Clear the screen and move cursor to top-left."""
        print(cls.CLEAR_AND_HOME, end="", flush=True)

    @classmethod
    def print_separator(
        cls, char: str = "=", width: int = 70, color: str = ""
    ) -> None:
        """Print a separator line."""
        line = char * width
        if color:
            line = f"{color}{line}{Colors.RESET}"
        print(line)
