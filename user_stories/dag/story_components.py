"""YAML-driven story component resolution.

Reads userstory_dag_data.yaml and provides:
1. Per-story filtered component lists (ordered)
2. Ordered marker sequences for GIF recording
3. Validation of component_filter entries against layer definitions

The YAML ``component_filter`` field on a story restricts which child-leaf
components are shown (and in which order) for each node in that story's
context.  When absent, all components are shown (backward compatibility).

Usage::

    from story_components import (
        load_dag_data, build_node_index, get_filtered_components,
        get_marker_sequence, get_story_by_id, validate_component_filters,
    )

    data = load_dag_data()
    node_index = build_node_index(data=data)
    story = get_story_by_id(data=data, story_id="US-1a.1")
    comps = get_filtered_components(
        story=story, node_id="cfg_1b1w", node_index=node_index
    )
    markers = get_marker_sequence(story=story, node_index=node_index)
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

DATA_FILE = Path(__file__).parent / "userstory_dag_data.yaml"


def load_dag_data(*, data_file: Path = DATA_FILE) -> Dict[str, Any]:
    """Load and return the full YAML data."""
    with open(data_file) as f:
        return yaml.safe_load(f)


def build_node_index(*, data: Dict[str, Any]) -> Dict[str, Dict]:
    """Build ``{node_id: {layer, layer_label, label, desc, components}}``."""
    idx: Dict[str, Dict] = {}
    for layer in data.get("layers", []):
        for node in layer.get("nodes", []):
            idx[node["id"]] = {
                "layer": layer["name"],
                "layer_label": layer["label"],
                "label": node["label"],
                "desc": node.get("desc", ""),
                "components": node.get("components", []),
            }
    return idx


def get_story_by_id(
    *, data: Dict[str, Any], story_id: str
) -> Optional[Dict]:
    """Find a story by its ID.  Returns ``None`` if not found."""
    for story in data.get("stories", []):
        if story["id"] == story_id:
            return story
    return None


def get_filtered_components(
    *,
    story: Dict,
    node_id: str,
    node_index: Dict[str, Dict],
) -> List[Dict]:
    """Return the filtered, ordered component list for a node in a story.

    If the story has a ``component_filter`` entry for *node_id*, return
    only those components in the specified order.  Otherwise return all
    components from the node definition.
    """
    all_components = node_index.get(node_id, {}).get("components", [])
    if not all_components:
        return []

    comp_filter = story.get("component_filter", {})
    if node_id not in comp_filter:
        return all_components

    allowed_ids = comp_filter[node_id]
    comp_by_id = {c["id"]: c for c in all_components}
    return [comp_by_id[cid] for cid in allowed_ids if cid in comp_by_id]


def get_marker_sequence(
    *,
    story: Dict,
    node_index: Dict[str, Dict],
    path_index: int = 0,
) -> List[str]:
    """Return the ordered list of ``@@NODE`` markers to emit for a story.

    The sequence interleaves node-level and sub-component markers::

        cfg_1b1w
        cfg_1b1w__bank_csv
        cfg_1b1w__dir_paths
        cat_basic
        cat_basic__groceries
        ...

    Args:
        story: Story dict from YAML.
        node_index: Output of :func:`build_node_index`.
        path_index: Which path to use (default 0 = first).

    Returns:
        Ordered list of marker ID strings (without ``@@NODE:`` prefix).
    """
    paths = story.get("demo_paths") or story.get("paths", [])
    if path_index >= len(paths):
        return []

    node_path = paths[path_index]
    markers: List[str] = []

    for node_id in node_path:
        markers.append(node_id)
        components = get_filtered_components(
            story=story, node_id=node_id, node_index=node_index
        )
        for comp in components:
            markers.append(f"{node_id}__{comp['id']}")

    return markers


def validate_component_filters(*, data: Dict[str, Any]) -> List[str]:
    """Validate all ``component_filter`` entries against layer definitions.

    Returns a list of error messages.  Empty list means valid.
    """
    node_index = build_node_index(data=data)
    errors: List[str] = []

    for story in data.get("stories", []):
        sid = story.get("id", "?")
        comp_filter = story.get("component_filter", {})
        if not comp_filter:
            continue

        path_nodes: set = set()
        for p in story.get("paths", []):
            path_nodes.update(p)

        for node_id, comp_ids in comp_filter.items():
            if node_id not in path_nodes:
                errors.append(
                    f"{sid}: component_filter references '{node_id}' "
                    f"which is not in any path"
                )
                continue

            all_comps = {
                c["id"]
                for c in node_index.get(node_id, {}).get("components", [])
            }
            for cid in comp_ids:
                if cid not in all_comps:
                    errors.append(
                        f"{sid}: component_filter[{node_id}] references "
                        f"unknown component '{cid}' "
                        f"(available: {sorted(all_comps)})"
                    )

    return errors
