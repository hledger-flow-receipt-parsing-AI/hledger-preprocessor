#!/usr/bin/env python3
"""Generate a static GitHub Pages site for browsing user stories.

Reads userstory_dag_data.yaml, discovers MP4 demo videos and .cast
recordings, and emits a static HTML site with:
- Landing page showing the full DAG overview
- Per-story pages with synchronized video + interactive SVG DAG
- Keyboard navigation (Up/Down) to jump between DAG nodes in the video

Usage:
    python generate_site.py --output site/
    python generate_site.py --output site/ --no-svg  # skip PlantUML SVG
"""

import argparse
import html as html_mod
import json
import re
import shutil
import subprocess
import tempfile
from collections import OrderedDict, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml
from story_components import (
    build_node_index,
    get_filtered_components,
    get_marker_sequence,
)

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
DATA_FILE = SCRIPT_DIR / "userstory_dag_data.yaml"
GIFS_ROOT = PROJECT_ROOT / "gifs"
RECEIPTS_ROOT = GIFS_ROOT / "assets" / "receipts"
OUTPUT_DIR_DEFAULT = SCRIPT_DIR / "site"

# Map story sections to GIF directories and cast file directories.
SECTION_TO_GIF_DIR: Dict[str, Optional[str]] = {
    "Step 1a: Account Configuration": "1a_setup_config",
    "Step 1b: Category Configuration": "1b_add_category",
    "Step 2a: Receipt Image Processing": "2a_crop_receipt",
    "Step 2b: Receipt Labelling": "2b_label_receipt",
    "Step 3: Receipt-to-CSV Transaction Matching": "3_match_receipt_to_csv",
    "Step 4: Pipeline Execution": "4_run_pipeline",
    "Step 5: Visualisation": "5_show_plots",
    "Transaction Classification": None,
    "Cross-cutting Concerns": None,
}

# Map story sections to the DAG layers that represent the section's primary
# work area (used for section boxing in the full-path DAG view).
SECTION_PRIMARY_LAYERS: Dict[str, List[str]] = {
    "Step 1a: Account Configuration": [
        "config_group",
    ],
    "Step 1b: Category Configuration": ["categories"],
    "Step 2a: Receipt Image Processing": ["receipt_img"],
    "Step 2b: Receipt Labelling": [
        "receipt_img",
        "receipt_group",
    ],
    "Step 3: Receipt-to-CSV Transaction Matching": [
        "csv_txn",
        "matching_out",
    ],
    "Step 4: Pipeline Execution": ["journal_out"],
    "Step 5: Visualisation": ["visualization"],
    "Transaction Classification": ["csv_txn", "journal_out"],
}

DEFAULT_THEME = "dracula"


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------
def load_data() -> Dict[str, Any]:
    """Load userstory_dag_data.yaml."""
    with open(DATA_FILE) as f:
        return yaml.safe_load(f)


def dag_stories(*, stories: List[Dict]) -> List[Dict]:
    """Filter to stories that have DAG paths."""
    return [s for s in stories if s.get("paths")]


def story_id_to_safe(*, story_id: str) -> str:
    """Convert story ID to safe filename: 'US-1a.1' -> 'US_1a_1'."""
    return story_id.replace(".", "_").replace("-", "_")


def group_stories_by_section(
    *, stories: List[Dict]
) -> "OrderedDict[str, List[Dict]]":
    """Group stories by their section field, preserving YAML order."""
    groups: OrderedDict[str, List[Dict]] = OrderedDict()
    for s in stories:
        sec = s.get("section", "Other")
        groups.setdefault(sec, []).append(s)
    return groups


# ---------------------------------------------------------------------------
# Video and cast file discovery
# ---------------------------------------------------------------------------
def discover_videos(*, gifs_root: Path, theme: str) -> Dict[str, Path]:
    """Find best MP4/GIF per GIF directory. Returns {dir_name: path}."""
    result: Dict[str, Path] = {}
    for gif_dir in sorted(gifs_root.iterdir()):
        out = gif_dir / "output"
        if not out.is_dir():
            continue
        name = gif_dir.name
        # Prefer {name}_{theme}.mp4
        candidates = sorted(out.glob(f"*{theme}*.mp4"))
        if not candidates:
            candidates = sorted(out.glob("*.mp4"))
        if not candidates:
            candidates = sorted(out.glob(f"*{theme}*.gif"))
        if not candidates:
            candidates = sorted(out.glob("*.gif"))
        if candidates:
            # Prefer file whose stem starts with the directory name
            best = candidates[0]
            for c in candidates:
                if c.stem.startswith(name):
                    best = c
                    break
            result[name] = best
    return result


def discover_all_videos(*, gifs_root: Path) -> Dict[str, Dict[str, Path]]:
    """Find ALL MP4/GIF files per GIF directory.

    Returns {dir_name: {stem: path}} — e.g.
    {"1a_setup_config": {"cfg_1b": Path(...cfg_1b.mp4), "cfg_2b": ...}}.
    Prefers .mp4 over .gif when both exist for the same stem.
    """
    result: Dict[str, Dict[str, Path]] = {}
    for gif_dir in sorted(gifs_root.iterdir()):
        out = gif_dir / "output"
        if not out.is_dir():
            continue
        name = gif_dir.name
        stem_map: Dict[str, Path] = {}
        # Collect GIFs first, then MP4s override (so MP4 wins)
        for ext in ["*.gif", "*.mp4"]:
            for f in sorted(out.glob(ext)):
                stem_map[f.stem] = f
        if stem_map:
            result[name] = stem_map
    return result


def discover_cast_files(*, gifs_root: Path) -> Dict[str, Path]:
    """Find best .cast file per GIF directory. Returns {dir_name: path}."""
    result: Dict[str, Path] = {}
    for gif_dir in sorted(gifs_root.iterdir()):
        rec = gif_dir / "recordings"
        if not rec.is_dir():
            continue
        name = gif_dir.name
        casts = sorted(rec.glob("*.cast"))
        if casts:
            best = casts[0]
            for c in casts:
                if c.stem.startswith(name):
                    best = c
                    break
            result[name] = best
    return result


NODE_MARKER_RE = re.compile(r"@@NODE:(\w+)@@")
# Comprehensive ANSI escape stripper: SGR, cursor movement, clear screen, etc.
_ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]|\x1b\].*?\x07")


def _build_rendered_times(
    *, cast_path: Path
) -> Tuple[List[Tuple[float, str]], List[float], float]:
    """Parse a .cast file and compute rendered (idle-compressed) timestamps.

    ``agg`` (v1.7.0) uses its own default ``--idle-time-limit`` of **5 s** as
    the threshold for detecting idle gaps.  Gaps exceeding this threshold are
    capped to the ``.cast`` header's ``idle_time_limit`` value (e.g. 2 s).
    We replicate this exact behaviour so that extracted marker timestamps
    match the rendered video.

    Returns ``(events, rendered_times, idle_limit)`` where *events* is a
    list of ``(raw_ts, data)`` tuples and *rendered_times* is the
    corresponding rendered timestamp for each event.
    """
    AGG_IDLE_THRESHOLD = 5.0  # agg's built-in default --idle-time-limit

    events: List[Tuple[float, str]] = []
    idle_limit: Optional[float] = None
    try:
        with open(cast_path) as f:
            header = json.loads(f.readline())
            idle_limit = header.get("idle_time_limit")
            for line in f:
                row = json.loads(line)
                events.append((row[0], row[2]))
    except (json.JSONDecodeError, OSError):
        return [], [], None

    rendered: List[float] = []
    rendered_t = 0.0
    prev_raw = 0.0
    for i, (raw_t, _data) in enumerate(events):
        if i == 0:
            rendered_t = raw_t
        else:
            gap = raw_t - prev_raw
            if gap > AGG_IDLE_THRESHOLD:
                gap = idle_limit if idle_limit else AGG_IDLE_THRESHOLD
            rendered_t += gap
        rendered.append(rendered_t)
        prev_raw = raw_t

    return events, rendered, idle_limit


def parse_cast_node_markers(*, cast_path: Path) -> Dict[str, float]:
    """Parse @@NODE:node_id@@ markers from a .cast file.

    Returns {node_id: first_timestamp_seconds} using rendered
    (idle-compressed) timestamps that match the GIF/MP4 output.
    """
    events, rendered, _idle = _build_rendered_times(cast_path=cast_path)
    markers: Dict[str, float] = {}
    for i, (raw_t, data) in enumerate(events):
        for m in NODE_MARKER_RE.finditer(data):
            nid = m.group(1)
            if nid not in markers:
                markers[nid] = round(rendered[i], 2)
    return markers


def get_video_for_section(
    *,
    section: str,
    video_map: Dict[str, Path],
) -> Optional[Path]:
    """Get the video path for a story section."""
    gif_dir = SECTION_TO_GIF_DIR.get(section)
    if gif_dir and gif_dir in video_map:
        return video_map[gif_dir]
    return None


def get_video_for_story(
    *,
    story: Dict,
    section: str,
    video_map: Dict[str, Path],
    all_videos: Dict[str, Dict[str, Path]],
) -> Optional[Path]:
    """Get the video path for a specific story.

    Uses the story's ``gif_video`` field to find a per-story video.
    First searches the section's GIF directory, then searches all
    directories (so stories can have GIFs in their own directory).
    Falls back to the section-level video.
    """
    gif_dir = SECTION_TO_GIF_DIR.get(section)
    gif_video = story.get("gif_video")
    if gif_video:
        # Try the section's GIF directory first
        if gif_dir and gif_dir in all_videos:
            dir_videos = all_videos[gif_dir]
            if gif_video in dir_videos:
                return dir_videos[gif_video]
        # Search all directories for the gif_video stem
        for _dir_name, dir_videos in all_videos.items():
            if gif_video in dir_videos:
                return dir_videos[gif_video]
    # Fallback to section-level default
    return get_video_for_section(section=section, video_map=video_map)


def get_markers_for_story(
    *,
    story: Dict,
    section: str,
    marker_json_map: Dict[str, Dict[str, Path]],
) -> Dict[str, float]:
    """Get marker timestamps for a specific story.

    Uses the story's ``gif_video`` field to find the matching sidecar
    markers JSON.  Searches the section directory first, then all
    directories.  Returns empty dict if none found.
    """
    gif_dir = SECTION_TO_GIF_DIR.get(section)
    gif_video = story.get("gif_video")
    if gif_video:
        # Try the section's GIF directory first
        if gif_dir and gif_dir in marker_json_map:
            dir_markers = marker_json_map[gif_dir]
            if gif_video in dir_markers:
                return parse_marker_json(json_path=dir_markers[gif_video])
        # Search all directories for the gif_video stem
        for _dir_name, dir_markers in marker_json_map.items():
            if gif_video in dir_markers:
                return parse_marker_json(json_path=dir_markers[gif_video])
    return {}


def get_cast_duration(*, cast_path: Path) -> float:
    """Return the rendered duration of a .cast file (with idle compression)."""
    _events, rendered, _idle = _build_rendered_times(cast_path=cast_path)
    if rendered:
        return round(rendered[-1], 2)
    return 0.0


def get_node_markers_for_section(
    *,
    section: str,
    cast_map: Dict[str, Path],
) -> Dict[str, float]:
    """Get per-node timestamps from @@NODE:xxx@@ markers in a cast file."""
    gif_dir = SECTION_TO_GIF_DIR.get(section)
    if gif_dir and gif_dir in cast_map:
        return parse_cast_node_markers(cast_path=cast_map[gif_dir])
    return {}


def get_cast_duration_for_section(
    *,
    section: str,
    cast_map: Dict[str, Path],
) -> float:
    """Get the duration in seconds of the cast file for a section."""
    gif_dir = SECTION_TO_GIF_DIR.get(section)
    if gif_dir and gif_dir in cast_map:
        return get_cast_duration(cast_path=cast_map[gif_dir])
    return 0.0


# ---------------------------------------------------------------------------
# Sidecar marker JSON discovery (from segmented GIF generation)
# ---------------------------------------------------------------------------
def discover_marker_json_files(
    *, gifs_root: Path
) -> Dict[str, Dict[str, Path]]:
    """Find ALL *_markers.json sidecar files in GIF output directories.

    Returns {dir_name: {stem: json_path}} — stem is the markers file name
    without the ``_markers.json`` suffix, e.g. ``{"1a_setup_config":
    {"cfg_1b": Path(...cfg_1b_markers.json), "cfg_2b": ...}}``.
    """
    result: Dict[str, Dict[str, Path]] = {}
    for gif_dir in sorted(gifs_root.iterdir()):
        out = gif_dir / "output"
        if not out.is_dir():
            continue
        name = gif_dir.name
        stem_map: Dict[str, Path] = {}
        for mf in sorted(out.glob("*_markers.json")):
            # e.g. cfg_1b_markers.json → stem = cfg_1b
            stem = mf.name.replace("_markers.json", "")
            stem_map[stem] = mf
        if stem_map:
            result[name] = stem_map
    return result


def parse_marker_json(*, json_path: Path) -> Dict[str, float]:
    """Read a sidecar markers JSON file and return {marker_id: timestamp_seconds}."""
    try:
        data = json.loads(json_path.read_text())
        return data.get("markers", {})
    except (json.JSONDecodeError, OSError):
        return {}


# ---------------------------------------------------------------------------
# SVG generation
# ---------------------------------------------------------------------------
def generate_svg(*, puml_path: Path) -> Optional[str]:
    """Run plantuml -tsvg on a .puml file, return SVG string or None."""
    if not puml_path.exists():
        return None
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            subprocess.run(
                ["plantuml", "-tsvg", "-o", tmpdir, str(puml_path)],
                capture_output=True,
                timeout=30,
            )
            svg_path = Path(tmpdir) / (puml_path.stem + ".svg")
            if svg_path.exists():
                return svg_path.read_text()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return None


def generate_overview_svg_direct(
    *,
    data: Dict,
    node_index: Dict[str, Dict],
    stories: List[Dict],
) -> str:
    """Generate the full-DAG overview SVG directly — no Graphviz.

    Layers are stacked top-to-bottom, all left-aligned.  Nodes are laid
    out horizontally within each layer.  Edges are drawn as quadratic
    Bézier curves between node centres.
    """
    from html import escape as html_escape

    # --- Import helpers from generate_userstory_artifacts ---
    from generate_userstory_artifacts import (
        CONFIG_GROUP_LAYERS,
        LAYER_COLOURS,
        LAYER_ORDER,
        RECEIPT_GROUP_LAYERS,
        collect_edges_from_paths,
        collect_nodes_from_paths,
        count_edge_usage,
        count_node_usage,
        penwidth_for_count,
    )

    # --- Collect visible nodes / edges / usage ---
    visible_nodes: set = set()
    visible_edges: set = set()
    for s in stories:
        visible_nodes.update(collect_nodes_from_paths(s["paths"]))
        visible_edges.update(collect_edges_from_paths(s["paths"]))

    node_usage = count_node_usage(stories)
    edge_usage = count_edge_usage(stories)

    # Group visible nodes by layer
    layer_nodes: Dict[str, List[str]] = defaultdict(list)
    for nid in visible_nodes:
        if nid in node_index:
            layer_nodes[node_index[nid]["layer"]].append(nid)
    for k in layer_nodes:
        layer_nodes[k].sort()

    # --- Layout constants ---
    MARGIN = 16
    NODE_W = 100  # node box width
    NODE_H = 24  # node box height
    NODE_PAD_X = 14  # horizontal gap between nodes
    NODE_PAD_Y = 3  # vertical padding inside cluster above/below nodes
    CLUSTER_PAD_TOP = 16  # space for cluster label
    CLUSTER_PAD_BOT = 4
    LAYER_GAP = 6  # vertical gap between layer clusters
    CONFIG_GROUP_PAD = 4  # horizontal padding for config parent box
    CONFIG_GROUP_TOP = 16  # extra top padding for "Configuration" label
    FONT_SIZE = 10
    LABEL_FONT_SIZE = 11

    # --- Compute positions ---
    # node_pos[nid] = (cx, cy) — centre of the node box
    node_pos: Dict[str, Tuple[float, float]] = {}
    # cluster_box[layer] = (x, y, w, h)
    cluster_box: Dict[str, Tuple[float, float, float, float]] = {}

    y_cursor = MARGIN
    max_width = 0.0

    ordered_layers = [ln for ln in LAYER_ORDER if ln in layer_nodes]

    # First config layer flag for the config group box
    config_y_start = None
    config_y_end = None
    config_max_right = 0.0  # rightmost edge among config child clusters

    # Receipt group tracking (mirrors config group pattern)
    RECEIPT_GROUP_PAD = CONFIG_GROUP_PAD
    RECEIPT_GROUP_TOP = CONFIG_GROUP_TOP
    receipt_y_start = None
    receipt_y_end = None
    receipt_max_right = 0.0

    for layer_name in ordered_layers:
        nids = layer_nodes[layer_name]
        n_nodes = len(nids)

        cluster_w = max(
            n_nodes * NODE_W + (n_nodes - 1) * NODE_PAD_X + 2 * MARGIN,
            200,  # minimum cluster width for label
        )
        cluster_h = CLUSTER_PAD_TOP + NODE_H + CLUSTER_PAD_BOT + NODE_PAD_Y

        # Add space for the "Configuration" label above the first config layer
        if layer_name in CONFIG_GROUP_LAYERS and config_y_start is None:
            y_cursor += CONFIG_GROUP_TOP

        # Add space for the "Receipt Labelling" label above the first receipt layer
        if layer_name in RECEIPT_GROUP_LAYERS and receipt_y_start is None:
            y_cursor += RECEIPT_GROUP_TOP

        cluster_x = MARGIN
        cluster_y = y_cursor

        cluster_box[layer_name] = (cluster_x, cluster_y, cluster_w, cluster_h)

        # Position nodes within the cluster, starting from the left
        node_start_x = cluster_x + MARGIN
        node_y = cluster_y + CLUSTER_PAD_TOP + NODE_PAD_Y

        for i, nid in enumerate(nids):
            cx = node_start_x + i * (NODE_W + NODE_PAD_X) + NODE_W / 2
            cy = node_y + NODE_H / 2
            node_pos[nid] = (cx, cy)

        if cluster_w + MARGIN > max_width:
            max_width = cluster_w + MARGIN

        # Track config group bounds
        if layer_name in CONFIG_GROUP_LAYERS:
            if config_y_start is None:
                config_y_start = cluster_y
            config_y_end = cluster_y + cluster_h
            right = cluster_x + cluster_w
            if right > config_max_right:
                config_max_right = right

        # Track receipt group bounds
        if layer_name in RECEIPT_GROUP_LAYERS:
            if receipt_y_start is None:
                receipt_y_start = cluster_y
            receipt_y_end = cluster_y + cluster_h
            right = cluster_x + cluster_w
            if right > receipt_max_right:
                receipt_max_right = right

        y_cursor += cluster_h + LAYER_GAP

    total_w = max_width + MARGIN * 2
    total_h = y_cursor + MARGIN

    # Config group box — sized to fit its children only, not all layers
    config_group_box = None
    if config_y_start is not None and config_y_end is not None:
        config_group_box = (
            MARGIN - CONFIG_GROUP_PAD,
            config_y_start - CONFIG_GROUP_TOP - CONFIG_GROUP_PAD,
            config_max_right - MARGIN + CONFIG_GROUP_PAD * 2,
            config_y_end
            - config_y_start
            + CONFIG_GROUP_TOP
            + CONFIG_GROUP_PAD * 2,
        )

    # Receipt group box
    receipt_group_box = None
    if receipt_y_start is not None and receipt_y_end is not None:
        receipt_group_box = (
            MARGIN - RECEIPT_GROUP_PAD,
            receipt_y_start - RECEIPT_GROUP_TOP - RECEIPT_GROUP_PAD,
            receipt_max_right - MARGIN + RECEIPT_GROUP_PAD * 2,
            receipt_y_end
            - receipt_y_start
            + RECEIPT_GROUP_TOP
            + RECEIPT_GROUP_PAD * 2,
        )

    # --- Edge routing ---
    # Dash pattern for SVG
    def svg_dash(pattern: str) -> str:
        return {
            "dashed": ' stroke-dasharray="8,4"',
            "dotted": ' stroke-dasharray="2,3"',
            "bold": "",
            "solid": "",
        }.get(pattern, "")

    # --- Build SVG ---
    lines: List[str] = []
    # viewBox placeholder — replaced at end once final total_w is known.
    lines.append(
        '<svg class="dag-svg" viewBox="__VIEWBOX__"'
        ' xmlns="http://www.w3.org/2000/svg"'
        ' xmlns:xlink="http://www.w3.org/1999/xlink">'
    )

    # Arrowhead markers — one grey for shared edges, one per story colour.
    # We collect all story colours and create a marker for each.
    arrow_colours: Dict[str, str] = {"_grey": "#CCC"}
    for s in stories:
        c = s.get("colour", "#7aa2f7")
        arrow_colours[c] = c
    lines.append("<defs>")
    for key, colour in arrow_colours.items():
        safe_id = re.sub(r"[^a-zA-Z0-9]", "", key)
        lines.append(
            f'<marker id="arrow_{safe_id}" viewBox="0 0 10 6"'
            ' refX="10" refY="3" markerWidth="10" markerHeight="8"'
            ' orient="auto-start-reverse">'
            f'<path d="M0,0 L10,3 L0,6 Z" fill="{colour}"/>'
            "</marker>"
        )
    lines.append("</defs>")

    # Config group parent box
    if config_group_box:
        gx, gy, gw, gh = config_group_box
        lines.append(
            '<g class="cluster dag-cluster" data-layer="config_group"><rect'
            f' x="{gx:.0f}" y="{gy:.0f}" width="{gw:.0f}" height="{gh:.0f}"'
            ' fill="none" stroke="#bbb" stroke-width="1.5"'
            f' stroke-dasharray="5,2" rx="4"/><text x="{gx + 10:.0f}"'
            f' y="{gy + 16:.0f}" font-family="DejaVu Sans,sans-serif"'
            f' font-size="{LABEL_FONT_SIZE}"'
            ' fill="#aaa">Configuration</text></g>'
        )

    # Receipt Labelling group parent box
    if receipt_group_box:
        gx, gy, gw, gh = receipt_group_box
        lines.append(
            '<g class="cluster dag-cluster" data-layer="receipt_group"><rect'
            f' x="{gx:.0f}" y="{gy:.0f}" width="{gw:.0f}" height="{gh:.0f}"'
            ' fill="none" stroke="#bbb" stroke-width="1.5"'
            f' stroke-dasharray="5,2" rx="4"/><text x="{gx + 10:.0f}"'
            f' y="{gy + 16:.0f}" font-family="DejaVu Sans,sans-serif"'
            f' font-size="{LABEL_FONT_SIZE}"'
            ' fill="#aaa">Receipt Labelling</text></g>'
        )

    # Layer clusters and nodes
    for layer_name in ordered_layers:
        nids = layer_nodes[layer_name]
        cx, cy, cw, ch = cluster_box[layer_name]
        fill = LAYER_COLOURS.get(layer_name, "#FFFFFF")
        layer_label = node_index[nids[0]]["layer_label"]

        lines.append(
            f'<g class="cluster dag-cluster" data-layer="{layer_name}">'
            f'<rect x="{cx:.0f}" y="{cy:.0f}" width="{cw:.0f}"'
            f' height="{ch:.0f}" fill="{fill}" stroke="#888" rx="3"/>'
            f'<text x="{cx + 8:.0f}" y="{cy + 15:.0f}"'
            ' font-family="DejaVu Sans,sans-serif"'
            f' font-size="{LABEL_FONT_SIZE}" fill="#333">'
            f"{html_escape(layer_label)}</text>"
            "</g>"
        )

        for nid in nids:
            info = node_index[nid]
            ncx, ncy = node_pos[nid]
            nx = ncx - NODE_W / 2
            ny = ncy - NODE_H / 2
            pw = penwidth_for_count(node_usage.get(nid, 1))
            label = info["label"].replace("\\n", "\n")
            html_escape(info["desc"])

            # Split multi-line label
            label_lines = label.split("\n")

            lines.append(
                f'<g class="node dag-node" data-layer="{info["layer"]}"'
                f' data-node="{nid}">'
                f'<a><title>{html_escape(info["desc"])}</title>'
                f'<rect x="{nx:.1f}" y="{ny:.1f}"'
                f' width="{NODE_W}" height="{NODE_H}"'
                f' fill="white" stroke="#333" stroke-width="{pw}" rx="3"/>'
            )
            if len(label_lines) == 1:
                lines.append(
                    f'<text x="{ncx:.1f}" y="{ncy + 4:.1f}"'
                    ' text-anchor="middle"'
                    ' font-family="DejaVu Sans,sans-serif"'
                    f' font-size="{FONT_SIZE}">{html_escape(label_lines[0])}</text>'
                )
            else:
                # Centre multiple lines vertically
                total_text_h = len(label_lines) * (FONT_SIZE + 2)
                start_y = ncy - total_text_h / 2 + FONT_SIZE
                for j, ln in enumerate(label_lines):
                    ty = start_y + j * (FONT_SIZE + 2)
                    lines.append(
                        f'<text x="{ncx:.1f}" y="{ty:.1f}"'
                        ' text-anchor="middle"'
                        ' font-family="DejaVu Sans,sans-serif"'
                        f' font-size="{FONT_SIZE}">{html_escape(ln)}</text>'
                    )
            lines.append("</a></g>")

    # --- Edge routing ---
    # Find the rightmost edge of any cluster so we can route long edges
    # around the outside.
    max_cluster_right = max(
        (cx + cw for cx, cy, cw, ch in cluster_box.values()), default=200
    )

    # Map layer_name -> index in ordered_layers for distance calculation
    layer_idx = {ln: i for i, ln in enumerate(ordered_layers)}

    # Track how many edges use each "routing lane" (right-side column)
    # so we can spread them out horizontally to avoid overlap.
    lane_counter: Dict[Tuple, int] = defaultdict(int)

    def edge_path(src: str, dst: str, lane_offset: float = 0) -> str:
        """Build an SVG path from src node bottom to dst node top.

        Adjacent layers: simple S-curve.
        Non-adjacent: route right, then down, then left to avoid boxes.
        """
        sx, sy = node_pos[src]
        tx, ty = node_pos[dst]
        s_bot = sy + NODE_H / 2  # source bottom
        t_top = ty - NODE_H / 2  # target top

        src_layer = node_index[src]["layer"]
        dst_layer = node_index[dst]["layer"]
        src_idx = layer_idx.get(src_layer, 0)
        dst_idx = layer_idx.get(dst_layer, 0)
        layer_gap = abs(dst_idx - src_idx)

        if layer_gap == 0:
            # Same layer — arc above the cluster box so the curve
            # doesn't pass through sibling node boxes.
            _, cy, _, _ = cluster_box[src_layer]
            arc_y = cy - 10 - lane_offset  # above the cluster
            return (
                f"M{sx:.1f},{sy - NODE_H/2:.1f}"
                f" C{sx:.1f},{arc_y:.1f} {tx:.1f},{arc_y:.1f}"
                f" {tx:.1f},{ty - NODE_H/2:.1f}"
            )
        elif layer_gap == 1:
            # Adjacent layers — simple S-curve between the two nodes.
            mid_y = (s_bot + t_top) / 2
            return (
                f"M{sx:.1f},{s_bot:.1f}"
                f" C{sx:.1f},{mid_y:.1f} {tx:.1f},{mid_y:.1f}"
                f" {tx:.1f},{t_top:.1f}"
            )
        else:
            # Non-adjacent: route to the right side, go down, come back.
            route_x = max_cluster_right + 20 + lane_offset
            # Small radius for corners
            gap = LAYER_GAP / 2
            return (
                f"M{sx:.1f},{s_bot:.1f}"
                f" L{sx:.1f},{s_bot + gap:.1f}"
                f" C{sx:.1f},{s_bot + gap + 8:.1f}"
                f" {route_x:.1f},{s_bot + gap + 8:.1f}"
                f" {route_x:.1f},{s_bot + gap + 16:.1f}"
                f" L{route_x:.1f},{t_top - gap - 16:.1f}"
                f" C{route_x:.1f},{t_top - gap - 8:.1f}"
                f" {tx:.1f},{t_top - gap - 8:.1f}"
                f" {tx:.1f},{t_top - gap:.1f}"
                f" L{tx:.1f},{t_top:.1f}"
            )

    # Collect all unique edges and assign lane offsets for long edges
    # to prevent overlapping paths on the right side.
    all_edges_to_draw: List[Tuple[str, str]] = []
    for src, dst in sorted(visible_edges):
        if src in node_pos and dst in node_pos:
            all_edges_to_draw.append((src, dst))

    # Assign lane offsets for non-adjacent edges (right-side routing)
    # and same-layer edges (arc height above cluster).
    edge_lane: Dict[Tuple[str, str], float] = {}
    long_lane_count = 0
    same_layer_lane: Dict[str, int] = defaultdict(int)  # per-layer counter
    for src, dst in all_edges_to_draw:
        src_layer = node_index[src]["layer"]
        dst_layer = node_index[dst]["layer"]
        src_idx = layer_idx.get(src_layer, 0)
        dst_idx = layer_idx.get(dst_layer, 0)
        gap = abs(dst_idx - src_idx)
        if gap > 1:
            edge_lane[(src, dst)] = long_lane_count * 8
            long_lane_count += 1
        elif gap == 0:
            edge_lane[(src, dst)] = same_layer_lane[src_layer] * 6
            same_layer_lane[src_layer] += 1
        else:
            edge_lane[(src, dst)] = 0
    lane_count = long_lane_count

    # Update total_w if long edges extend past the right side
    if lane_count > 0:
        needed_w = max_cluster_right + 20 + lane_count * 8 + MARGIN
        if needed_w > total_w:
            total_w = needed_w

    # --- Edges ---
    # First pass: grey base for shared edges
    for (src, dst), count in sorted(edge_usage.items()):
        if src in node_pos and dst in node_pos and count > 1:
            pw = penwidth_for_count(count, True)
            d = edge_path(src, dst, edge_lane.get((src, dst), 0))
            lines.append(
                f'<g class="edge dag-edge" data-source="{src}"'
                f' data-target="{dst}">'
                f'<path d="{d}"'
                f' fill="none" stroke="#CCC" stroke-width="{pw}"'
                ' marker-end="url(#arrow_grey)"/>'
                "</g>"
            )

    # Second pass: coloured edges per story
    for s in stories:
        story_edges = collect_edges_from_paths(s["paths"])
        colour = s.get("colour", "#7aa2f7")
        pattern = s.get("pattern", "solid")
        dash = svg_dash(pattern)
        arrow_id = "arrow_" + re.sub(r"[^a-zA-Z0-9]", "", colour)
        for src, dst in sorted(story_edges):
            if src in node_pos and dst in node_pos:
                d = edge_path(src, dst, edge_lane.get((src, dst), 0))
                lines.append(
                    f'<g class="edge dag-edge" data-source="{src}"'
                    f' data-target="{dst}">'
                    f'<path d="{d}"'
                    f' fill="none" stroke="{colour}"'
                    f' stroke-width="1.5"{dash}'
                    f' marker-end="url(#{arrow_id})"/>'
                    "</g>"
                )

    lines.append("</svg>")
    result = "\n".join(lines)
    # Fill in the viewBox now that total_w is final
    result = result.replace("__VIEWBOX__", f"0 0 {total_w:.0f} {total_h:.0f}")
    return result


def generate_story_svg_direct(
    *,
    node_ids: List[str],
    node_index: Dict[str, Dict],
    paths: List[List[str]],
    story_colour: str = "#7aa2f7",
    highlight_layers: Optional[List[str]] = None,
    svg_id_prefix: str = "",
) -> str:
    """Generate a per-story SVG showing only the given nodes.

    Uses a two-column layout when many layers are present: left column
    holds config/pre-receipt layers, right column holds receipt-labelling
    and post-receipt layers.  The right column starts vertically below the
    (typically wider) account-config layer to save horizontal space.

    Args:
        node_ids: Node IDs to include.
        node_index: Full node index from ``build_node_index()``.
        paths: The story's paths (used to derive edges among visible nodes).
        story_colour: Edge colour.
        highlight_layers: Optional list of layer names to highlight with a
            section box in the full-path view.
    """
    from html import escape as html_escape

    from generate_userstory_artifacts import (
        CONFIG_GROUP_LAYERS,
        LAYER_COLOURS,
        LAYER_ORDER,
        RECEIPT_GROUP_LAYERS,
    )

    # --- Collect visible nodes / edges ---
    visible_nodes: set = set(node_ids)
    # Derive edges: only between consecutive nodes that are BOTH visible
    visible_edges: set = set()
    for path in paths:
        filtered = [n for n in path if n in visible_nodes]
        for i in range(len(filtered) - 1):
            visible_edges.add((filtered[i], filtered[i + 1]))

    # Group visible nodes by layer
    layer_nodes: Dict[str, List[str]] = defaultdict(list)
    for nid in visible_nodes:
        if nid in node_index:
            layer_nodes[node_index[nid]["layer"]].append(nid)
    for k in layer_nodes:
        layer_nodes[k].sort()

    if not layer_nodes:
        return (
            '<svg class="dag-svg" viewBox="0 0 200 40"'
            ' xmlns="http://www.w3.org/2000/svg"></svg>'
        )

    # --- Layout constants ---
    MARGIN = 16
    NODE_W = 100
    NODE_H = 22  # compact height for per-story views
    NODE_PAD_X = 14
    NODE_PAD_Y = 2
    CLUSTER_PAD_TOP = 14
    CLUSTER_PAD_BOT = 3
    LAYER_GAP = 8  # increased for arrow visibility
    CONFIG_GROUP_PAD = 3
    CONFIG_GROUP_TOP = 14
    COL_GAP = 20  # horizontal gap between left and right columns
    FONT_SIZE = 9
    LABEL_FONT_SIZE = 10
    MIN_CLUSTER_W = 132  # tight minimum cluster width (node=100 + 2*MARGIN)

    ordered_layers = [ln for ln in LAYER_ORDER if ln in layer_nodes]

    # --- Determine 2-column split ---
    # The right column starts at the first RECEIPT_GROUP_LAYER.
    # Left column: all layers before that.  Right column: receipt group + rest.
    # Only use 2-column if there are enough layers (>6) and a receipt group.
    receipt_split_idx = None
    for i, ln in enumerate(ordered_layers):
        if ln in RECEIPT_GROUP_LAYERS:
            receipt_split_idx = i
            break

    use_two_columns = (
        receipt_split_idx is not None and len(ordered_layers) >= 7
    )

    if use_two_columns:
        left_layers = ordered_layers[:receipt_split_idx]
        right_layers = ordered_layers[receipt_split_idx:]
    else:
        left_layers = ordered_layers
        right_layers = []

    # --- Helper: compute cluster width for a layer ---
    def _cluster_w(layer_name: str) -> float:
        n = len(layer_nodes[layer_name])
        return max(
            n * NODE_W + (n - 1) * NODE_PAD_X + 2 * MARGIN,
            MIN_CLUSTER_W,
        )

    def _cluster_h() -> float:
        return CLUSTER_PAD_TOP + NODE_H + CLUSTER_PAD_BOT + NODE_PAD_Y

    # --- Compute positions ---
    node_pos: Dict[str, Tuple[float, float]] = {}
    cluster_box: Dict[str, Tuple[float, float, float, float]] = {}

    config_y_start = None
    config_y_end = None
    config_max_right = 0.0
    config_first_layer_bottom = None  # bottom of the first (widest) config layer

    RECEIPT_GROUP_PAD = CONFIG_GROUP_PAD
    RECEIPT_GROUP_TOP = CONFIG_GROUP_TOP
    receipt_y_start = None
    receipt_y_end = None
    receipt_max_right = 0.0

    # Layout left column
    y_cursor = MARGIN
    left_max_width = 0.0

    for layer_name in left_layers:
        cw = _cluster_w(layer_name)
        ch = _cluster_h()

        if layer_name in CONFIG_GROUP_LAYERS and config_y_start is None:
            y_cursor += CONFIG_GROUP_TOP

        cluster_x = MARGIN
        cluster_y = y_cursor
        cluster_box[layer_name] = (cluster_x, cluster_y, cw, ch)

        node_start_x = cluster_x + MARGIN
        node_y = cluster_y + CLUSTER_PAD_TOP + NODE_PAD_Y
        for i, nid in enumerate(layer_nodes[layer_name]):
            cx = node_start_x + i * (NODE_W + NODE_PAD_X) + NODE_W / 2
            cy = node_y + NODE_H / 2
            node_pos[nid] = (cx, cy)

        if cw + MARGIN > left_max_width:
            left_max_width = cw + MARGIN

        if layer_name in CONFIG_GROUP_LAYERS:
            if config_y_start is None:
                config_y_start = cluster_y
                config_first_layer_bottom = cluster_y + ch
            config_y_end = cluster_y + ch
            right = cluster_x + cw
            if right > config_max_right:
                config_max_right = right

        y_cursor += ch + LAYER_GAP

    left_col_bottom = y_cursor

    # Layout right column (if 2-column)
    right_col_x = 0.0
    right_max_width = 0.0

    if use_two_columns and right_layers:
        # Right column x: position so that the leftmost right-column node
        # nearly touches the rightmost left-column node (~2px gap).
        # Rightmost left node edge = left_max_width - MARGIN.
        # Leftmost right node left edge = right_col_x + MARGIN.
        # So: right_col_x + MARGIN = left_max_width - MARGIN + 2  →
        right_col_x = left_max_width - 2 * MARGIN + 2

        # Right column y starts just below the first (widest) config layer
        # to form a "P-shape" / reversed-L layout that minimises height.
        if config_first_layer_bottom is not None:
            right_y_start = config_first_layer_bottom + LAYER_GAP
        else:
            right_y_start = MARGIN

        y_cursor_r = right_y_start

        for layer_name in right_layers:
            cw = _cluster_w(layer_name)
            ch = _cluster_h()

            if layer_name in RECEIPT_GROUP_LAYERS and receipt_y_start is None:
                y_cursor_r += RECEIPT_GROUP_TOP

            cluster_x = right_col_x
            cluster_y = y_cursor_r
            cluster_box[layer_name] = (cluster_x, cluster_y, cw, ch)

            node_start_x = cluster_x + MARGIN
            node_y = cluster_y + CLUSTER_PAD_TOP + NODE_PAD_Y
            for i, nid in enumerate(layer_nodes[layer_name]):
                cx = node_start_x + i * (NODE_W + NODE_PAD_X) + NODE_W / 2
                cy = node_y + NODE_H / 2
                node_pos[nid] = (cx, cy)

            if cw > right_max_width:
                right_max_width = cw

            if layer_name in RECEIPT_GROUP_LAYERS:
                if receipt_y_start is None:
                    receipt_y_start = cluster_y
                receipt_y_end = cluster_y + ch
                right = cluster_x + cw
                if right > receipt_max_right:
                    receipt_max_right = right

            y_cursor_r += ch + LAYER_GAP

        right_col_bottom = y_cursor_r
    else:
        # Single column: layout remaining layers in the same column
        for layer_name in right_layers:
            cw = _cluster_w(layer_name)
            ch = _cluster_h()

            if layer_name in RECEIPT_GROUP_LAYERS and receipt_y_start is None:
                y_cursor += RECEIPT_GROUP_TOP

            cluster_x = MARGIN
            cluster_y = y_cursor
            cluster_box[layer_name] = (cluster_x, cluster_y, cw, ch)

            node_start_x = cluster_x + MARGIN
            node_y = cluster_y + CLUSTER_PAD_TOP + NODE_PAD_Y
            for i, nid in enumerate(layer_nodes[layer_name]):
                cx = node_start_x + i * (NODE_W + NODE_PAD_X) + NODE_W / 2
                cy = node_y + NODE_H / 2
                node_pos[nid] = (cx, cy)

            if cw + MARGIN > left_max_width:
                left_max_width = cw + MARGIN

            if layer_name in RECEIPT_GROUP_LAYERS:
                if receipt_y_start is None:
                    receipt_y_start = cluster_y
                receipt_y_end = cluster_y + ch
                right = cluster_x + cw
                if right > receipt_max_right:
                    receipt_max_right = right

            y_cursor += ch + LAYER_GAP

        right_col_bottom = y_cursor

    # Compute total dimensions
    if use_two_columns:
        total_w = right_col_x + right_max_width + MARGIN * 2
        total_h = max(left_col_bottom, right_col_bottom) + MARGIN
    else:
        total_w = left_max_width + MARGIN * 2
        total_h = right_col_bottom + MARGIN

    # Config group box
    config_group_box = None
    if config_y_start is not None and config_y_end is not None:
        config_group_box = (
            MARGIN - CONFIG_GROUP_PAD,
            config_y_start - CONFIG_GROUP_TOP - CONFIG_GROUP_PAD,
            config_max_right - MARGIN + CONFIG_GROUP_PAD * 2,
            config_y_end
            - config_y_start
            + CONFIG_GROUP_TOP
            + CONFIG_GROUP_PAD * 2,
        )

    # Receipt group box
    receipt_group_box = None
    if receipt_y_start is not None and receipt_y_end is not None:
        receipt_group_box = (
            receipt_y_start
            and (cluster_box[right_layers[0]][0] if use_two_columns else MARGIN)
            or MARGIN,
            receipt_y_start - RECEIPT_GROUP_TOP - RECEIPT_GROUP_PAD,
            receipt_max_right
            - (right_col_x if use_two_columns else MARGIN)
            + RECEIPT_GROUP_PAD * 2,
            receipt_y_end
            - receipt_y_start
            + RECEIPT_GROUP_TOP
            + RECEIPT_GROUP_PAD * 2,
        )
        # Recalculate properly: x should be the right column x minus pad
        if use_two_columns:
            rcpt_x = right_col_x - RECEIPT_GROUP_PAD
        else:
            rcpt_x = MARGIN - RECEIPT_GROUP_PAD
        receipt_group_box = (
            rcpt_x,
            receipt_y_start - RECEIPT_GROUP_TOP - RECEIPT_GROUP_PAD,
            receipt_max_right - (right_col_x if use_two_columns else MARGIN)
            + RECEIPT_GROUP_PAD * 2,
            receipt_y_end
            - receipt_y_start
            + RECEIPT_GROUP_TOP
            + RECEIPT_GROUP_PAD * 2,
        )

    # --- Edge routing helpers ---
    def svg_dash(pattern: str) -> str:
        return {
            "dashed": ' stroke-dasharray="8,4"',
            "dotted": ' stroke-dasharray="2,3"',
            "bold": "",
            "solid": "",
        }.get(pattern, "")

    layer_idx = {ln: i for i, ln in enumerate(ordered_layers)}
    max_cluster_right = max(
        (cx + cw for cx, cy, cw, ch in cluster_box.values()), default=200
    )

    # Track which column each layer belongs to for cross-column edges
    right_layer_set = set(right_layers) if use_two_columns else set()

    def edge_path(src: str, dst: str, lane_offset: float = 0) -> str:
        sx, sy = node_pos[src]
        tx, ty = node_pos[dst]
        s_bot = sy + NODE_H / 2
        t_top = ty - NODE_H / 2

        src_layer = node_index[src]["layer"]
        dst_layer = node_index[dst]["layer"]
        src_li = layer_idx.get(src_layer, 0)
        dst_li = layer_idx.get(dst_layer, 0)
        layer_gap = abs(dst_li - src_li)

        # Cross-column edge (left col -> right col)
        src_in_right = src_layer in right_layer_set
        dst_in_right = dst_layer in right_layer_set
        if use_two_columns and not src_in_right and dst_in_right:
            # Route: go down from source, curve right, go up to target
            mid_x = (sx + tx) / 2
            return (
                f"M{sx:.1f},{s_bot:.1f}"
                f" C{sx:.1f},{s_bot + 20:.1f}"
                f" {tx:.1f},{t_top - 20:.1f}"
                f" {tx:.1f},{t_top:.1f}"
            )

        if layer_gap == 0:
            _, cy, _, _ = cluster_box[src_layer]
            arc_y = cy - 10 - lane_offset
            return (
                f"M{sx:.1f},{sy - NODE_H/2:.1f}"
                f" C{sx:.1f},{arc_y:.1f} {tx:.1f},{arc_y:.1f}"
                f" {tx:.1f},{ty - NODE_H/2:.1f}"
            )
        elif layer_gap == 1:
            mid_y = (s_bot + t_top) / 2
            return (
                f"M{sx:.1f},{s_bot:.1f}"
                f" C{sx:.1f},{mid_y:.1f} {tx:.1f},{mid_y:.1f}"
                f" {tx:.1f},{t_top:.1f}"
            )
        else:
            route_x = max_cluster_right + 20 + lane_offset
            gap = LAYER_GAP / 2
            return (
                f"M{sx:.1f},{s_bot:.1f}"
                f" L{sx:.1f},{s_bot + gap:.1f}"
                f" C{sx:.1f},{s_bot + gap + 8:.1f}"
                f" {route_x:.1f},{s_bot + gap + 8:.1f}"
                f" {route_x:.1f},{s_bot + gap + 16:.1f}"
                f" L{route_x:.1f},{t_top - gap - 16:.1f}"
                f" C{route_x:.1f},{t_top - gap - 8:.1f}"
                f" {tx:.1f},{t_top - gap - 8:.1f}"
                f" {tx:.1f},{t_top - gap:.1f}"
                f" L{tx:.1f},{t_top:.1f}"
            )

    # --- Assign lane offsets ---
    all_edges_to_draw: List[Tuple[str, str]] = []
    for src, dst in sorted(visible_edges):
        if src in node_pos and dst in node_pos:
            all_edges_to_draw.append((src, dst))

    edge_lane: Dict[Tuple[str, str], float] = {}
    long_lane_count = 0
    same_layer_lane: Dict[str, int] = defaultdict(int)
    for src, dst in all_edges_to_draw:
        src_layer = node_index[src]["layer"]
        dst_layer = node_index[dst]["layer"]
        src_li = layer_idx.get(src_layer, 0)
        dst_li = layer_idx.get(dst_layer, 0)
        gap = abs(dst_li - src_li)
        if gap > 1:
            edge_lane[(src, dst)] = long_lane_count * 8
            long_lane_count += 1
        elif gap == 0:
            edge_lane[(src, dst)] = same_layer_lane[src_layer] * 6
            same_layer_lane[src_layer] += 1
        else:
            edge_lane[(src, dst)] = 0

    if long_lane_count > 0:
        needed_w = max_cluster_right + 20 + long_lane_count * 8 + MARGIN
        if needed_w > total_w:
            total_w = needed_w

    # --- Build SVG ---
    lines: List[str] = []
    lines.append(
        '<svg class="dag-svg" viewBox="__VIEWBOX__"'
        ' xmlns="http://www.w3.org/2000/svg"'
        ' xmlns:xlink="http://www.w3.org/1999/xlink">'
    )

    # Arrow marker — larger for visibility.
    # Use svg_id_prefix to avoid duplicate marker IDs when multiple SVGs
    # appear on the same HTML page (segment view + full-path view).
    safe_colour = re.sub(r"[^a-zA-Z0-9]", "", story_colour)
    marker_id_base = f"{svg_id_prefix}arrow_{safe_colour}"
    lines.append("<defs>")
    lines.append(
        f'<marker id="{marker_id_base}" viewBox="0 0 10 6"'
        ' refX="10" refY="3" markerWidth="10" markerHeight="8"'
        ' orient="auto-start-reverse">'
        f'<path d="M0,0 L10,3 L0,6 Z" fill="{story_colour}"/>'
        "</marker>"
    )
    lines.append("</defs>")

    # Config group parent box
    hl_layers = set(highlight_layers or [])
    if config_group_box:
        gx, gy, gw, gh = config_group_box
        cfg_cls = " section-box" if "config_group" in hl_layers else ""
        cfg_stroke = (
            "var(--accent, #2563eb)" if "config_group" in hl_layers else "#bbb"
        )
        cfg_sw = "2.5" if "config_group" in hl_layers else "1.5"
        lines.append(
            f'<g class="cluster dag-cluster{cfg_cls}"'
            f' data-layer="config_group"><rect x="{gx:.0f}" y="{gy:.0f}"'
            f' width="{gw:.0f}" height="{gh:.0f}" fill="none"'
            f' stroke="{cfg_stroke}" stroke-width="{cfg_sw}"'
            f' stroke-dasharray="5,2" rx="4"/><text x="{gx + 10:.0f}"'
            f' y="{gy + 16:.0f}" font-family="DejaVu Sans,sans-serif"'
            f' font-size="{LABEL_FONT_SIZE}"'
            ' fill="#aaa">Configuration</text></g>'
        )

    # Receipt Labelling group parent box
    if receipt_group_box:
        gx, gy, gw, gh = receipt_group_box
        rcpt_cls = " section-box" if "receipt_group" in hl_layers else ""
        rcpt_stroke = (
            "var(--accent, #2563eb)"
            if "receipt_group" in hl_layers
            else "#bbb"
        )
        rcpt_sw = "2.5" if "receipt_group" in hl_layers else "1.5"
        lines.append(
            f'<g class="cluster dag-cluster{rcpt_cls}"'
            f' data-layer="receipt_group"><rect x="{gx:.0f}" y="{gy:.0f}"'
            f' width="{gw:.0f}" height="{gh:.0f}" fill="none"'
            f' stroke="{rcpt_stroke}" stroke-width="{rcpt_sw}"'
            f' stroke-dasharray="5,2" rx="4"/><text x="{gx + 10:.0f}"'
            f' y="{gy + 16:.0f}" font-family="DejaVu Sans,sans-serif"'
            f' font-size="{LABEL_FONT_SIZE}"'
            ' fill="#aaa">Receipt Labelling</text></g>'
        )

    # Layer clusters and nodes
    for layer_name in ordered_layers:
        nids = layer_nodes[layer_name]
        cx, cy, cw, ch = cluster_box[layer_name]
        fill = LAYER_COLOURS.get(layer_name, "#FFFFFF")
        layer_label = node_index[nids[0]]["layer_label"]

        extra_cls = " section-box" if layer_name in hl_layers else ""
        extra_style = ""
        if layer_name in hl_layers:
            extra_style = ' stroke-dasharray="8 4" stroke-width="2.5"'

        lines.append(
            f'<g class="cluster dag-cluster{extra_cls}"'
            f' data-layer="{layer_name}"><rect x="{cx:.0f}" y="{cy:.0f}"'
            f' width="{cw:.0f}" height="{ch:.0f}" fill="{fill}" stroke="#888"'
            f' rx="3"{extra_style}/><text x="{cx + 8:.0f}" y="{cy + 15:.0f}"'
            ' font-family="DejaVu Sans,sans-serif"'
            f' font-size="{LABEL_FONT_SIZE}"'
            f' fill="#333">{html_escape(layer_label)}</text></g>'
        )

        for nid in nids:
            info = node_index[nid]
            ncx, ncy = node_pos[nid]
            nx = ncx - NODE_W / 2
            ny = ncy - NODE_H / 2
            label = info["label"].replace("\\n", "\n")
            label_lines = label.split("\n")

            lines.append(
                f'<g class="node dag-node" data-layer="{info["layer"]}"'
                f' data-node="{nid}">'
                f'<a><title>{html_escape(info["desc"])}</title>'
                f'<rect x="{nx:.1f}" y="{ny:.1f}"'
                f' width="{NODE_W}" height="{NODE_H}"'
                ' fill="white" stroke="#333" stroke-width="1" rx="3"/>'
            )
            if len(label_lines) == 1:
                lines.append(
                    f'<text x="{ncx:.1f}" y="{ncy + 4:.1f}"'
                    ' text-anchor="middle"'
                    ' font-family="DejaVu Sans,sans-serif"'
                    f' font-size="{FONT_SIZE}">{html_escape(label_lines[0])}</text>'
                )
            else:
                total_text_h = len(label_lines) * (FONT_SIZE + 2)
                start_y = ncy - total_text_h / 2 + FONT_SIZE
                for j, ln in enumerate(label_lines):
                    ty = start_y + j * (FONT_SIZE + 2)
                    lines.append(
                        f'<text x="{ncx:.1f}" y="{ty:.1f}"'
                        ' text-anchor="middle"'
                        ' font-family="DejaVu Sans,sans-serif"'
                        f' font-size="{FONT_SIZE}">{html_escape(ln)}</text>'
                    )
            lines.append("</a></g>")

    # --- Edges ---
    arrow_id = marker_id_base
    for src, dst in all_edges_to_draw:
        d = edge_path(src, dst, edge_lane.get((src, dst), 0))
        lines.append(
            f'<g class="edge dag-edge" data-source="{src}"'
            f' data-target="{dst}">'
            f'<path d="{d}"'
            f' fill="none" stroke="{story_colour}"'
            ' stroke-width="1.5"'
            f' marker-end="url(#{arrow_id})"/>'
            "</g>"
        )

    lines.append("</svg>")
    result = "\n".join(lines)
    result = result.replace("__VIEWBOX__", f"0 0 {total_w:.0f} {total_h:.0f}")
    return result


def add_data_attributes_to_svg(*, svg: str, node_index: Dict[str, Dict]) -> str:
    """Post-process SVG to add data-layer and data-node attributes to nodes.

    PlantUML/Graphviz outputs nodes as <g> with a <title> containing the
    node ID. We add data attributes and a CSS class for JS targeting.
    """
    # For each node ID, add class and data attributes to its <g> parent
    for node_id, info in node_index.items():
        # Match: <title>node_id</title> and add attributes to parent <g>
        old = f"<title>{node_id}</title>"
        if old in svg:
            # Find the <g ...> that precedes this <title>
            pos = svg.index(old)
            # Search backwards for <g
            g_start = svg.rfind("<g ", 0, pos)
            if g_start >= 0:
                g_end = svg.index(">", g_start)
                g_tag = svg[g_start : g_end + 1]
                # Merge with existing class attribute if present
                if 'class="' in g_tag:
                    new_g = re.sub(
                        r'class="([^"]*)"',
                        f'class="\\1 dag-node" data-layer="{info["layer"]}"'
                        f' data-node="{node_id}"',
                        g_tag,
                        count=1,
                    )
                else:
                    new_g = g_tag.replace(
                        ">",
                        f' class="dag-node" data-layer="{info["layer"]}"'
                        f' data-node="{node_id}">',
                        1,
                    )
                svg = svg[:g_start] + new_g + svg[g_end + 1 :]

    # Also add data-layer to cluster groups (including config parent group)
    for layer_name in [
        "config_group",
        "config_accounts",
        "config_dir_paths",
        "config_file_names",
        "config_categorisation",
        "config_matching_algo",
        "categories",
        "matching_cfg",
        "start_journal",
        "csv_txn",
        "receipt_img",
        "receipt_lbl_before",
        "receipt_lbl_tui",
        "receipt_lbl_after",
        "matching_out",
        "journal_out",
        "visualization",
    ]:
        old = f"<title>cluster_{layer_name}</title>"
        if old in svg:
            pos = svg.index(old)
            g_start = svg.rfind("<g ", 0, pos)
            if g_start >= 0:
                g_end = svg.index(">", g_start)
                g_tag = svg[g_start : g_end + 1]
                if 'class="' in g_tag:
                    new_g = re.sub(
                        r'class="([^"]*)"',
                        f'class="\\1 dag-cluster" data-layer="{layer_name}"',
                        g_tag,
                        count=1,
                    )
                else:
                    new_g = g_tag.replace(
                        ">",
                        f' class="dag-cluster" data-layer="{layer_name}">',
                        1,
                    )
                svg = svg[:g_start] + new_g + svg[g_end + 1 :]

    # Add data attributes to edges for JS targeting
    # Edges have <title>source&#45;&gt;target</title> inside <g class="edge">
    edge_title_re = re.compile(r"<title>([^<]+&#45;&gt;[^<]+)</title>")
    search_start = 0
    while True:
        m = edge_title_re.search(svg, search_start)
        if not m:
            break
        title_text = html_mod.unescape(
            m.group(1)
        )  # e.g. "malgo_default->cat_basic"
        parts = title_text.split("->")
        if len(parts) == 2:
            src, tgt = parts[0].strip(), parts[1].strip()
            pos = m.start()
            g_start = svg.rfind("<g ", 0, pos)
            if g_start >= 0:
                g_end = svg.index(">", g_start)
                g_tag = svg[g_start : g_end + 1]
                if 'class="' in g_tag:
                    new_g = re.sub(
                        r'class="([^"]*)"',
                        f'class="\\1 dag-edge" data-source="{src}"'
                        f' data-target="{tgt}"',
                        g_tag,
                        count=1,
                    )
                else:
                    new_g = g_tag.replace(
                        ">",
                        f' class="dag-edge" data-source="{src}"'
                        f' data-target="{tgt}">',
                        1,
                    )
                len_diff = len(new_g) - len(g_tag)
                svg = svg[:g_start] + new_g + svg[g_end + 1 :]
                search_start = m.end() + len_diff
                continue
        search_start = m.end()

    # Make the SVG background transparent (first polygon is usually the bg)
    svg = re.sub(
        r'(<polygon fill=")white(" stroke="transparent")',
        r"\1none\2",
        svg,
        count=1,
    )

    # Make SVG responsive: strip fixed width/height (in pt), keep viewBox,
    # and add class. The viewBox is already set by PlantUML/Graphviz.
    svg = re.sub(r'\s*width="[^"]*"', "", svg, count=1)
    svg = re.sub(r'\s*height="[^"]*"', "", svg, count=1)
    svg = svg.replace("<svg", '<svg class="dag-svg"', 1)

    # Inject arrowhead markers into PlantUML SVGs so edges have visible arrows.
    # Add a <defs> block right after the opening <svg> tag.
    arrow_defs = (
        "<defs>"
        '<marker id="puml-arrow" viewBox="0 0 10 6" '
        'refX="10" refY="3" markerWidth="8" markerHeight="6" '
        'orient="auto-start-reverse">'
        '<path d="M0,0 L10,3 L0,6 Z" fill="#333"/>'
        "</marker>"
        "</defs>"
    )
    # Insert after the first '>' of the <svg> tag
    svg_tag_end = svg.find(">", svg.find("<svg"))
    if svg_tag_end >= 0:
        svg = svg[: svg_tag_end + 1] + arrow_defs + svg[svg_tag_end + 1 :]

    # Add marker-end to edge paths (edges have class "dag-edge")
    # PlantUML edge paths are inside <g class="...dag-edge..."> groups
    # and use <path> elements. Add marker-end to those paths.
    svg = re.sub(
        r'(<g[^>]*class="[^"]*dag-edge[^"]*"[^>]*>.*?<path\b[^>]*)(/>)',
        r'\1 marker-end="url(#puml-arrow)"\2',
        svg,
        flags=re.DOTALL,
    )

    return svg


# ---------------------------------------------------------------------------
# HTML / CSS / JS generation
# ---------------------------------------------------------------------------
def generate_css(*, dim_opacity: Optional[float] = None) -> str:
    """Generate the site stylesheet.

    Args:
        dim_opacity: Opacity for non-used/unreachable nodes (0.0–1.0).
                     Defaults to 0.18.  Edge opacity is derived as
                     ``dim_opacity * 0.6``.  Explorer dimmed values use
                     ``dim_opacity * 0.5`` for nodes and ``dim_opacity * 0.33``
                     for edges.
    """
    node_op = dim_opacity if dim_opacity is not None else 0.18
    edge_op = round(node_op * 0.6, 2)
    explorer_node_op = round(node_op * 0.5, 2)
    explorer_edge_op = round(node_op * 0.33, 2)
    css = """\
:root {
  --sidebar-width: 220px;
  --bg: #1a1b26;
  --bg-sidebar: #16161e;
  --bg-card: #24283b;
  --text: #c0caf5;
  --text-muted: #565f89;
  --accent: #7aa2f7;
  --accent-glow: rgba(122, 162, 247, 0.4);
  --border: #3b4261;
  --success: #9ece6a;
  --warning: #e0af68;
  --error: #f7768e;
}
@media (prefers-color-scheme: light) {
  :root {
    --bg: #f5f5f5; --bg-sidebar: #e8e8e8; --bg-card: #ffffff;
    --text: #1a1b26; --text-muted: #6b7280; --accent: #2563eb;
    --accent-glow: rgba(37, 99, 235, 0.3); --border: #d1d5db;
    --success: #16a34a; --warning: #d97706; --error: #dc2626;
  }
}
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background: var(--bg); color: var(--text);
  display: flex; min-height: 100vh;
}
a { color: var(--accent); text-decoration: none; }
a:hover { text-decoration: underline; }

/* Sidebar */
.sidebar {
  width: var(--sidebar-width); background: var(--bg-sidebar);
  border-right: 1px solid var(--border); padding: 0.5rem 0.6rem;
  position: fixed; top: 0; left: 0; bottom: 0;
  overflow-y: auto; z-index: 10;
}
.sidebar h1 { font-size: 1rem; margin-bottom: 1rem; }
.sidebar h1 a { color: var(--text); }
.sidebar details { margin-bottom: 0.5rem; }
.sidebar summary {
  cursor: pointer; font-weight: 600; font-size: 0.85rem;
  padding: 0.3rem 0; color: var(--text-muted);
  list-style: none;
}
.sidebar summary::-webkit-details-marker { display: none; }
.sidebar summary::before { content: '▸ '; }
.sidebar details[open] > summary::before { content: '▾ '; }
.sidebar ul { list-style: none; padding-left: 0.8rem; }
.sidebar li { padding: 0.15rem 0; }
.sidebar li a {
  font-size: 0.8rem; color: var(--text-muted);
  display: block; padding: 0.15rem 0.4rem; border-radius: 3px;
}
.sidebar li a:hover, .sidebar li a.active, .sidebar li a.explorer-active {
  color: var(--accent); background: var(--bg-card); text-decoration: none;
}

/* Main content */
.main {
  margin-left: var(--sidebar-width); flex: 1;
  padding: 0.75rem 1rem;
}
.main h1 { font-size: 1.5rem; margin-bottom: 0.5rem; }
.main h2 { font-size: 1.1rem; margin: 1.5rem 0 0.5rem; color: var(--accent); }

/* Story header */
.story-header {
  border-left: 4px solid var(--accent);
  padding: 1rem; margin-bottom: 1.5rem;
  background: var(--bg-card); border-radius: 0 8px 8px 0;
}
.story-header .story-id {
  font-size: 0.8rem; color: var(--text-muted);
  text-transform: uppercase; letter-spacing: 0.05em;
}
.story-header h1 { margin-top: 0.25rem; }
.badge {
  display: inline-block; font-size: 0.7rem; padding: 0.15rem 0.5rem;
  border-radius: 10px; font-weight: 600; margin-left: 0.5rem;
}
.badge-impl { background: var(--success); color: #000; }
.badge-not-impl { background: var(--warning); color: #000; }
.badge-wontfix { background: var(--error); color: #fff; }
.story-title-inline {
  font-size: 1.1rem; font-weight: 700;
}

/* Compact BDD narrative */
.bdd-compact {
  font-size: 0.85rem; margin-top: 0.4rem; line-height: 1.5;
  color: var(--text);
}
.bdd-kw {
  font-weight: 700; color: var(--accent); font-size: 0.8rem;
  text-transform: lowercase;
}

/* Receipt image — zoom-pane floated left inside story header */
.receipt-pane {
  float: left; margin: 0 1rem 0.5rem 0;
  position: relative;
  transition: box-shadow 0.3s ease;
}
.receipt-pane.active {
  box-shadow: 0 0 12px 4px var(--accent-glow);
  border-radius: 6px;
}
.receipt-image-inline {
  max-height: 280px; width: auto;
  border-radius: 6px; border: 1px solid var(--border);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
  display: block;
}
/* Receipt field bounding box overlay */
.receipt-overlay {
  position: absolute; top: 0; left: 0;
  width: 100%; height: 100%;
  pointer-events: none;
}
.receipt-overlay rect {
  fill: none; stroke: var(--accent); stroke-width: 1.5;
  opacity: 0; transition: opacity 0.3s ease;
}
.receipt-overlay rect.active { opacity: 0.85; }

/* Legacy receipt image section (kept for compatibility) */
.receipt-image-section {
  margin-bottom: 1.5rem;
  text-align: center;
}
.receipt-image {
  max-height: 350px;
  width: auto;
  border-radius: 8px;
  border: 1px solid var(--border);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
}

/* Video player */
.video-section { margin-bottom: 1.5rem; }
.video-section video, .video-section img {
  width: 100%; border-radius: 8px; border: 1px solid var(--border);
}
.video-hint {
  font-size: 0.75rem; color: var(--text-muted);
  margin-top: 0.3rem; text-align: center;
}

/* DAG diagram */
.dag-section { margin-bottom: 1.5rem; }
.dag-header {
  display: flex; justify-content: space-between; align-items: center;
  margin-bottom: 0.5rem;
}
.dag-header h2 { margin: 0; }
.dag-view-toggle { display: flex; gap: 0; }
.toggle-btn {
  font-size: 0.75rem; padding: 0.3rem 0.7rem;
  border: 1px solid var(--border); background: var(--bg-card);
  color: var(--text-muted); cursor: pointer; transition: all 0.15s;
}
.toggle-btn:first-child { border-radius: 4px 0 0 4px; }
.toggle-btn:last-child { border-radius: 0 4px 4px 0; border-left: none; }
.toggle-btn.active {
  background: var(--accent); color: #fff; border-color: var(--accent);
}
.toggle-btn:hover:not(.active) { color: var(--text); }
.dag-svg {
  width: 100%; height: auto;
  background: transparent;
}
.dag-fallback-img {
  max-width: 100%; height: auto;
  background: transparent;
}

/* Side-by-side video + DAG grid */
.video-dag-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.75rem;
  margin-bottom: 1rem;
}
.video-dag-row .video-section {
  grid-column: 1; grid-row: 1;
  margin-bottom: 0;
}
.video-dag-row .dag-section {
  grid-column: 2; grid-row: 1 / span 3;
  margin-bottom: 0;
}
.video-dag-row .below-row {
  grid-column: 1; grid-row: 2;
}

/* DAG node highlighting */
.dag-node { cursor: pointer; transition: opacity 0.2s; }
.dag-node.unreachable { cursor: default; opacity: __NODE_OP__; pointer-events: none; }
.dag-edge.unreachable { opacity: __EDGE_OP__; pointer-events: none; }
.dag-node.active polygon,
.dag-node.active ellipse,
.dag-node.active rect { stroke: #ff6600 !important; stroke-width: 3 !important; }
.dag-node.active text { font-weight: bold !important; }
.dag-cluster.active-cluster > polygon { stroke: #ff6600 !important; stroke-width: 2 !important; }

/* Section boxing in full-path view */
.dag-cluster.section-box > polygon,
.dag-cluster.section-box > path {
  stroke: var(--accent) !important;
  stroke-width: 2.5 !important;
  stroke-dasharray: 8 4 !important;
  fill: rgba(122, 162, 247, 0.06) !important;
}

/* Layer indicator */
.layer-indicator {
  background: var(--bg-card); border: 1px solid var(--border);
  border-radius: 6px; padding: 0.5rem 1rem; margin-bottom: 1rem;
  font-size: 0.85rem; display: flex; align-items: center; gap: 0.5rem;
}
.layer-indicator .layer-dot {
  width: 10px; height: 10px; border-radius: 50%;
  background: var(--accent); display: inline-block;
}
.layer-indicator .layer-name { font-weight: 600; }

/* Navigation hints bar */
.nav-hints {
  display: flex; flex-wrap: wrap; gap: 1rem;
  font-size: 0.72rem; color: var(--text-muted);
  background: var(--bg-card); border: 1px solid var(--border);
  border-radius: 6px; padding: 0.4rem 0.8rem; margin-bottom: 1rem;
}
.nav-hints kbd {
  display: inline-block; padding: 0.05rem 0.3rem;
  background: var(--bg); border: 1px solid var(--border);
  border-radius: 3px; font-size: 0.65rem; font-family: inherit;
  vertical-align: baseline;
}

/* BDD narrative */
.bdd { background: var(--bg-card); padding: 1rem; border-radius: 8px; margin-bottom: 1rem; }
.bdd dt { font-weight: 700; color: var(--accent); font-size: 0.85rem; margin-top: 0.5rem; }
.bdd dd { margin-left: 1rem; font-size: 0.9rem; }

/* Acceptance criteria */
.criteria { margin-bottom: 1rem; }
.criteria li {
  padding: 0.3rem 0; font-size: 0.9rem;
  list-style: none; padding-left: 1.5rem; position: relative;
}
.criteria li::before {
  content: '☐'; position: absolute; left: 0; color: var(--text-muted);
}

/* DAG path display */
.dag-path {
  display: flex; flex-wrap: nowrap; gap: 0.3rem;
  align-items: flex-start; margin-bottom: 1rem;
  overflow-x: auto;
}
.dag-path .path-node {
  font-size: 0.75rem; padding: 0.3rem 0.5rem;
  background: var(--bg-card); border: 1px solid var(--border);
  border-radius: 4px; cursor: default; transition: all 0.15s;
  display: flex; flex-direction: column; text-align: center;
}
.dag-path .path-node:not(.clickable) { opacity: 0.45; }
.dag-path .path-node.clickable { cursor: pointer; }
.dag-path .path-node .path-layer-name {
  font-size: 0.6rem; text-transform: uppercase; letter-spacing: 0.04em;
  color: var(--text-muted); display: block; margin-bottom: 0.1rem;
  font-weight: 600;
}
.dag-path .path-node.clickable:hover { border-color: var(--accent); }
.dag-path .path-node.active {
  border-color: #ff6600; background: rgba(255, 102, 0, 0.15);
  font-weight: 600;
}
.dag-path .path-arrow { color: var(--text-muted); font-size: 0.7rem; align-self: center; flex-shrink: 0; }
.dag-path > .path-node { flex-shrink: 0; }

/* Tree chip groups */
.path-node-group { display: inline-flex; flex-direction: column; flex-shrink: 0; }
.path-children {
  display: none; flex-direction: column; gap: 0.15rem;
  margin-top: 0.2rem; padding-left: 0.5rem;
}
.path-children.expanded { display: flex; }
.path-child {
  font-size: 0.65rem; padding: 0.2rem 0.4rem;
  background: var(--bg-card); border: 1px solid var(--border);
  border-radius: 3px; cursor: default; transition: all 0.15s;
  white-space: nowrap;
}
.path-child:not(.clickable) { opacity: 0.45; }
.path-child.clickable { cursor: pointer; }
.path-child.clickable:hover { border-color: var(--accent); }
.path-child.active {
  border-color: #ff6600; background: rgba(255, 102, 0, 0.15);
  font-weight: 600;
}
.expand-indicator { font-size: 0.6rem; margin-left: 0.3rem; }

/* Navigation */
.nav-links {
  display: flex; justify-content: space-between;
  margin-top: 2rem; padding-top: 1rem;
  border-top: 1px solid var(--border);
}
.nav-links a {
  padding: 0.5rem 1rem; border-radius: 6px;
  background: var(--bg-card); border: 1px solid var(--border);
}
.nav-links a:hover { border-color: var(--accent); text-decoration: none; }

/* Landing page */
.coming-soon {
  text-align: center; padding: 2rem;
  color: var(--text-muted); font-style: italic;
  background: var(--bg-card); border-radius: 8px;
  border: 1px dashed var(--border);
}

/* DAG Explorer (index page) */
.dag-explorer {
  position: relative; overflow: hidden; cursor: grab;
  border: 1px solid var(--border); border-radius: 8px;
  background: transparent;
  min-height: calc(100vh - 8rem);
}
.dag-explorer:active { cursor: grabbing; }
.dag-explorer .dag-svg {
  transform-origin: 0 0; transition: transform 0.15s ease-out;
  width: 100%; height: auto;
}
.dag-explorer .dag-node.dimmed { opacity: __EXPLORER_NODE_OP__; transition: opacity 0.3s; }
.dag-explorer .dag-edge.dimmed { opacity: __EXPLORER_EDGE_OP__; transition: opacity 0.3s; }
.dag-explorer .dag-node.story-hl polygon,
.dag-explorer .dag-node.story-hl ellipse,
.dag-explorer .dag-node.story-hl rect {
  stroke-width: 3 !important; filter: drop-shadow(0 0 6px var(--accent-glow));
}
.dag-explorer .dag-node.story-hl text { font-weight: bold !important; }
.dag-explorer .dag-cluster.cluster-hl > polygon {
  stroke-width: 2 !important; filter: drop-shadow(0 0 4px var(--accent-glow));
}

.explorer-status {
  position: absolute; bottom: 0; left: 0; right: 0;
  background: rgba(22, 22, 30, 0.92); backdrop-filter: blur(8px);
  border-top: 1px solid var(--border);
  padding: 0.6rem 1.2rem; display: flex; align-items: center; gap: 1rem;
  font-size: 0.85rem; z-index: 5;
}
@media (prefers-color-scheme: light) {
  .explorer-status { background: rgba(245, 245, 245, 0.92); }
}
.explorer-status .story-counter {
  font-weight: 700; color: var(--accent); min-width: 4.5em; text-align: center;
}
.explorer-status .story-title {
  flex: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.explorer-status .story-line-swatch {
  flex-shrink: 0; width: 32px; height: 14px;
}
.explorer-status .hints {
  font-size: 0.7rem; color: var(--text-muted); white-space: nowrap;
}
.explorer-status kbd {
  display: inline-block; padding: 0.1rem 0.35rem;
  background: var(--bg); border: 1px solid var(--border);
  border-radius: 3px; font-size: 0.65rem; font-family: inherit;
}

/* Zoom panes — independently zoomable regions */
.zoom-pane {
  position: relative; transition: outline-color 0.15s;
  outline: 2px solid transparent; outline-offset: -2px; border-radius: 4px;
}
.zoom-pane.zoom-selected {
  outline-color: var(--accent);
}
.zoom-pane-inner {
  transition: zoom 0.1s ease-out;
}
.zoom-indicator {
  position: absolute; top: 4px; right: 4px;
  font-size: 0.65rem; padding: 0.15rem 0.4rem;
  background: var(--bg-card); border: 1px solid var(--border);
  border-radius: 3px; color: var(--text-muted); z-index: 5;
  opacity: 0; transition: opacity 0.2s; pointer-events: none;
}
.zoom-pane.zoom-selected .zoom-indicator,
.zoom-pane:hover .zoom-indicator { opacity: 1; }
.zoom-resize-buttons {
  position: absolute; top: 4px; left: 4px;
  display: flex; gap: 2px; z-index: 5;
  opacity: 0; transition: opacity 0.2s;
}
.zoom-pane.zoom-selected .zoom-resize-buttons,
.zoom-pane:hover .zoom-resize-buttons { opacity: 1; }
.zoom-resize-btn {
  width: 22px; height: 22px; padding: 0; border: 1px solid var(--border);
  border-radius: 3px; background: var(--bg-card); color: var(--text-muted);
  font-size: 0.8rem; cursor: pointer; display: flex; align-items: center;
  justify-content: center; line-height: 1;
}
.zoom-resize-btn:hover { background: var(--accent); color: #fff; }
.sidebar.zoom-pane { position: fixed; overflow-y: auto; }
"""
    return (
        css.replace("__NODE_OP__", str(node_op))
        .replace("__EDGE_OP__", str(edge_op))
        .replace("__EXPLORER_NODE_OP__", str(explorer_node_op))
        .replace("__EXPLORER_EDGE_OP__", str(explorer_edge_op))
    )


def generate_js() -> str:
    """Generate the video-DAG synchronization JavaScript module.

    Per-story SVGs are generated with only the relevant nodes, so there
    is no need for unreachable-node graying.  The DAG itself is the
    navigation element — clicking a node jumps the video, and the current
    node is highlighted during playback.
    """
    return """\
(function() {
  'use strict';
  var svgContainer = document.querySelector('.dag-section');

  // Phase 1: Segment / Full-path view toggle (works even without video)
  var btnSegment = document.getElementById('btn-segment-view');
  var btnFull = document.getElementById('btn-full-view');
  var segmentView = document.getElementById('dag-segment-view');
  var fullView = document.getElementById('dag-full-view');

  if (btnSegment && btnFull && segmentView && fullView) {
    window._dagSetView = function(mode) {
      if (mode === 'full') {
        segmentView.style.display = 'none';
        fullView.style.display = '';
        btnFull.classList.add('active');
        btnSegment.classList.remove('active');
      } else {
        segmentView.style.display = '';
        fullView.style.display = 'none';
        btnSegment.classList.add('active');
        btnFull.classList.remove('active');
      }
      try { localStorage.setItem('dag-view-mode', mode); } catch(e) {}
    };

    btnSegment.addEventListener('click', function() { window._dagSetView('segment'); });
    btnFull.addEventListener('click', function() { window._dagSetView('full'); });

    // Restore saved preference
    try {
      var saved = localStorage.getItem('dag-view-mode');
      if (saved === 'full') window._dagSetView('full');
    } catch(e) {}
  }

  // Phase 2: Video synchronization (only when <video> element exists)
  var video = document.getElementById('demo-video');
  if (!video || !svgContainer || typeof TIMESTAMPS === 'undefined') return;

  // Build ordered list of parent-node timestamp keys (exclude sub-component keys)
  var tsKeys = Object.keys(TIMESTAMPS)
    .filter(function(k) { return TIMESTAMPS[k] !== null && k.indexOf('__') === -1; })
    .sort(function(a, b) { return TIMESTAMPS[a] - TIMESTAMPS[b]; });
  if (tsKeys.length === 0) return;

  var currentIdx = 0;
  var allNodes = svgContainer.querySelectorAll('.dag-node');
  var clusters = svgContainer.querySelectorAll('.dag-cluster');
  var layerIndicator = document.getElementById('layer-indicator-name');

  // Build a lookup: node_id -> layer name (from SVG data attributes)
  var nodeToLayer = {};
  allNodes.forEach(function(n) {
    var nid = n.getAttribute('data-node');
    var lay = n.getAttribute('data-layer');
    if (nid && lay) nodeToLayer[nid] = lay;
  });

  // Receipt pane and overlay elements
  var receiptPane = document.querySelector('.receipt-pane');
  var overlayRects = document.querySelectorAll('.receipt-overlay rect');

  // Map sub-component timestamp keys to receipt field IDs, grouped by parent
  var fieldTimestamps = {};
  var fieldsByParent = {};
  Object.keys(TIMESTAMPS).forEach(function(k) {
    var parts = k.split('__');
    if (parts.length === 2 && TIMESTAMPS[k] !== null) {
      fieldTimestamps[k] = { field: parts[1], time: TIMESTAMPS[k], parent: parts[0] };
      if (!fieldsByParent[parts[0]]) fieldsByParent[parts[0]] = [];
      fieldsByParent[parts[0]].push(k);
    }
  });
  // Sort each parent's field keys by time
  Object.keys(fieldsByParent).forEach(function(p) {
    fieldsByParent[p].sort(function(a, b) { return fieldTimestamps[a].time - fieldTimestamps[b].time; });
  });

  // Debug overlay (toggle with 'd' key)
  var debugEl = null;
  var debugVisible = false;
  function ensureDebugEl() {
    if (!debugEl) {
      debugEl = document.createElement('div');
      debugEl.style.cssText = 'position:fixed;bottom:8px;right:8px;background:rgba(0,0,0,0.85);color:#0f0;font:11px/1.4 monospace;padding:8px 12px;border-radius:4px;z-index:9999;pointer-events:none;max-width:340px;white-space:pre';
      document.body.appendChild(debugEl);
    }
  }
  function updateDebug(videoTime, nodeId, activeField) {
    if (!debugVisible) return;
    ensureDebugEl();
    var lines = ['t=' + (videoTime !== undefined ? videoTime.toFixed(2) : '?') + 's'];
    lines.push('node=' + nodeId);
    lines.push('field=' + (activeField || '(none)'));
    // Show field timestamp ranges for the active TUI node
    var parentKeys = fieldsByParent[nodeId];
    if (parentKeys) {
      lines.push('---');
      for (var i = 0; i < parentKeys.length; i++) {
        var e = fieldTimestamps[parentKeys[i]];
        var marker = (e.field === activeField) ? '>' : ' ';
        var nextTime = (i + 1 < parentKeys.length) ? fieldTimestamps[parentKeys[i + 1]].time : null;
        var range = e.time.toFixed(2) + (nextTime ? '-' + nextTime.toFixed(2) : '+');
        lines.push(marker + ' ' + e.field + ' ' + range);
      }
    }
    debugEl.textContent = lines.join('\\n');
  }

  function highlightReceiptField(nodeId, videoTime) {
    if (receiptPane) {
      var isReceiptNode = nodeId.indexOf('img_') === 0 ||
        nodeId.indexOf('nolbl_') === 0 ||
        nodeId.indexOf('tui_') === 0 ||
        nodeId.indexOf('lbl_') === 0;
      if (isReceiptNode) {
        receiptPane.classList.add('active');
      } else {
        receiptPane.classList.remove('active');
      }
    }
    var activeFields = {};
    if (overlayRects.length > 0 && videoTime !== undefined) {
      var isTuiNode = nodeId.indexOf('tui_') === 0;
      if (isTuiNode) {
        // Find the most recent marker timestamp <= videoTime, then
        // highlight ALL fields that share that same timestamp (e.g.
        // date + time are one combined TUI field).
        var nodeFieldKeys = fieldsByParent[nodeId] || [];
        var activeTime = -1;
        for (var i = 0; i < nodeFieldKeys.length; i++) {
          var entry = fieldTimestamps[nodeFieldKeys[i]];
          if (entry.time <= videoTime) activeTime = entry.time;
        }
        if (activeTime >= 0) {
          for (var i = 0; i < nodeFieldKeys.length; i++) {
            var entry = fieldTimestamps[nodeFieldKeys[i]];
            if (entry.time === activeTime) activeFields[entry.field] = true;
          }
        }
      }
      overlayRects.forEach(function(r) {
        r.classList.toggle('active', !!activeFields[r.getAttribute('data-field')]);
      });
    }
    updateDebug(videoTime, nodeId, Object.keys(activeFields).join(','));
  }

  function highlightNode(nodeId) {
    allNodes.forEach(function(n) { n.classList.remove('active'); });
    clusters.forEach(function(c) { c.classList.remove('active-cluster'); });

    // Highlight the specific node in both SVG views
    var targetLayer = nodeToLayer[nodeId] || '';
    allNodes.forEach(function(n) {
      if (n.getAttribute('data-node') === nodeId) {
        n.classList.add('active');
      }
    });

    // Highlight the cluster for this node's layer
    if (targetLayer) {
      clusters.forEach(function(c) {
        if (c.getAttribute('data-layer') === targetLayer) {
          c.classList.add('active-cluster');
        }
      });
    }

    // Update layer indicator
    if (layerIndicator) {
      layerIndicator.textContent = targetLayer.replace(/_/g, ' ') || nodeId;
    }

    // Highlight receipt image and field bounding boxes
    highlightReceiptField(nodeId, video ? video.currentTime : undefined);

    // Update currentIdx
    var idx = tsKeys.indexOf(nodeId);
    if (idx >= 0) currentIdx = idx;
  }

  // Sync: video time -> node highlight
  video.addEventListener('timeupdate', function() {
    var t = video.currentTime;
    var active = tsKeys[0];
    for (var i = 0; i < tsKeys.length; i++) {
      if (TIMESTAMPS[tsKeys[i]] <= t) active = tsKeys[i];
    }
    highlightNode(active);
  });

  // Keyboard: Up/Down jump between parent timestamped nodes
  document.addEventListener('keydown', function(e) {
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
    if (e.key === 'ArrowDown' || e.key === 'j') {
      e.preventDefault();
      currentIdx = Math.min(currentIdx + 1, tsKeys.length - 1);
      video.currentTime = TIMESTAMPS[tsKeys[currentIdx]];
      video.play();
    } else if (e.key === 'ArrowUp' || e.key === 'k') {
      e.preventDefault();
      currentIdx = Math.max(currentIdx - 1, 0);
      video.currentTime = TIMESTAMPS[tsKeys[currentIdx]];
      video.play();
    } else if (e.key === ' ' && e.target === document.body) {
      e.preventDefault();
      if (video.paused) video.play();
      else video.pause();
    } else if (e.key === 'd') {
      debugVisible = !debugVisible;
      if (debugEl) debugEl.style.display = debugVisible ? '' : 'none';
      if (debugVisible) highlightNode(tsKeys[currentIdx]);
    }
  });

  // Click DAG node -> jump video (both views)
  svgContainer.querySelectorAll('.dag-node').forEach(function(node) {
    node.addEventListener('click', function() {
      var nid = node.getAttribute('data-node');
      if (nid && TIMESTAMPS[nid] !== undefined) {
        video.currentTime = TIMESTAMPS[nid];
        video.play();
      }
    });
  });

  // Initialize with first timestamped node
  highlightNode(tsKeys[0]);

  // Phase 3: Extend view toggle with video-aware behaviour
  if (typeof fullView !== 'undefined' && fullView) {
    // Enhance _dagSetView with highlight re-binding
    var origSetView = window._dagSetView;
    window._dagSetView = function(mode) {
      origSetView(mode);
      var activeView = mode === 'full' ? fullView : segmentView;
      allNodes = activeView.querySelectorAll('.dag-node');
      clusters = activeView.querySelectorAll('.dag-cluster');
      nodeToLayer = {};
      allNodes.forEach(function(n) {
        var nid = n.getAttribute('data-node');
        var lay = n.getAttribute('data-layer');
        if (nid && lay) nodeToLayer[nid] = lay;
      });
      if (tsKeys.length > 0) highlightNode(tsKeys[currentIdx]);
    };

    // Re-apply saved preference now that video highlight works
    try {
      var saved = localStorage.getItem('dag-view-mode');
      if (saved === 'full') window._dagSetView('full');
    } catch(e) {}
  }
})();
"""


def generate_explorer_js() -> str:
    """Generate the DAG explorer JavaScript for the index page.

    Expects globals: STORIES (array of {id, title, colour, paths, url}).
    The SVG must already have data-node attributes from add_data_attributes_to_svg.
    """
    return r"""
(function() {
  'use strict';
  var explorer = document.querySelector('.dag-explorer');
  var svg = explorer && explorer.querySelector('svg');
  if (!explorer || !svg || typeof STORIES === 'undefined') return;

  var allNodes = explorer.querySelectorAll('.dag-node');
  var allEdges = explorer.querySelectorAll('.dag-edge');
  var clusters = explorer.querySelectorAll('.dag-cluster');
  var statusEl = document.getElementById('explorer-status');
  var counterEl = document.getElementById('explorer-counter');
  var titleEl = document.getElementById('explorer-title');
  var swatchEl = document.getElementById('explorer-swatch');
  var hintsEl = document.getElementById('explorer-hints');

  // --- State ---
  var scale = 1;
  var panX = 0, panY = 0;
  var storyIdx = -1;  // -1 = overview mode
  var ZOOM_STEP = 0.15;
  var MIN_ZOOM = 0.3;
  var MAX_ZOOM = 5;

  // Pan state for mouse drag
  var dragging = false, dragStartX = 0, dragStartY = 0, panStartX = 0, panStartY = 0;

  // --- Helpers ---
  function applyTransform() {
    svg.style.transform = 'translate(' + panX + 'px,' + panY + 'px) scale(' + scale + ')';
  }

  function contentBBox() {
    // Compute a bounding box from clusters and nodes only
    // (skipping the background polygon that spans the full viewBox).
    var minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
    var items = svg.querySelectorAll('.dag-cluster, .dag-node, .dag-edge');
    for (var i = 0; i < items.length; i++) {
      try {
        var b = items[i].getBBox();
        if (b.width > 0 && b.height > 0) {
          if (b.x < minX) minX = b.x;
          if (b.y < minY) minY = b.y;
          if (b.x + b.width > maxX) maxX = b.x + b.width;
          if (b.y + b.height > maxY) maxY = b.y + b.height;
        }
      } catch(e) {}
    }
    if (minX === Infinity) return svg.getBBox();
    return {x: minX, y: minY, width: maxX - minX, height: maxY - minY};
  }

  function resetView() {
    // Fit the DAG content (clusters + nodes) into the explorer container,
    // positioned at the top-left.  We use contentBBox() instead of
    // svg.getBBox() because the latter includes the invisible background
    // polygon that spans the entire viewBox.
    var bbox = contentBBox();
    var containerW = explorer.clientWidth;
    var containerH = explorer.clientHeight;
    if (bbox.width > 0 && bbox.height > 0 && containerW > 0 && containerH > 0) {
      var scaleH = containerH / bbox.height;
      var scaleW = containerW / bbox.width;
      scale = Math.min(scaleH, scaleW, 1.5);
      panX = -bbox.x * scale;
      panY = -bbox.y * scale;
    } else {
      scale = 1; panX = 0; panY = 0;
    }
    applyTransform();
  }

  function zoom(delta, cx, cy) {
    var oldScale = scale;
    scale = Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, scale + delta));
    var ratio = scale / oldScale;
    panX = cx - ratio * (cx - panX);
    panY = cy - ratio * (cy - panY);
    applyTransform();
  }

  function storyNodeSet(story) {
    var s = {};
    (story.paths || []).forEach(function(p) {
      p.forEach(function(nid) { s[nid] = true; });
    });
    return s;
  }

  function layersForNodes(nodeSet) {
    var layers = {};
    allNodes.forEach(function(n) {
      var nid = n.getAttribute('data-node');
      if (nid && nodeSet[nid]) {
        var lay = n.getAttribute('data-layer');
        if (lay) layers[lay] = true;
      }
    });
    return layers;
  }

  function clearHighlights() {
    allNodes.forEach(function(n) {
      n.classList.remove('dimmed', 'story-hl');
      n.querySelectorAll('polygon, ellipse, rect').forEach(function(el) {
        el.style.removeProperty('stroke');
      });
    });
    allEdges.forEach(function(e) { e.classList.remove('dimmed'); });
    clusters.forEach(function(c) { c.classList.remove('cluster-hl'); });
  }

  function highlightStory(idx) {
    clearHighlights();
    if (idx < 0 || idx >= STORIES.length) {
      statusEl.style.display = 'none';
      document.querySelectorAll('.sidebar li a.explorer-active').forEach(function(a) {
        a.classList.remove('explorer-active');
      });
      return;
    }
    var story = STORIES[idx];
    var ns = storyNodeSet(story);
    var ls = layersForNodes(ns);

    allNodes.forEach(function(n) {
      var nid = n.getAttribute('data-node');
      if (nid && ns[nid]) {
        n.classList.add('story-hl');
        n.querySelectorAll('polygon, ellipse, rect').forEach(function(el) {
          el.style.stroke = story.colour;
        });
      } else {
        n.classList.add('dimmed');
      }
    });
    // Match edges by stroke colour — each story has a unique colour on its edges
    var storyColour = story.colour.toLowerCase();
    allEdges.forEach(function(e) {
      var path = e.querySelector('path');
      var poly = e.querySelector('polygon');
      var edgeColour = '';
      if (path) edgeColour = (path.getAttribute('stroke') || '').toLowerCase();
      if (!edgeColour && poly) edgeColour = (poly.getAttribute('stroke') || '').toLowerCase();
      if (edgeColour === storyColour) {
        // This edge belongs to the current story — keep visible
      } else {
        e.classList.add('dimmed');
      }
    });
    clusters.forEach(function(c) {
      if (ls[c.getAttribute('data-layer')]) c.classList.add('cluster-hl');
    });

    statusEl.style.display = '';
    counterEl.textContent = (idx + 1) + ' / ' + STORIES.length;
    titleEl.textContent = story.id + ' \u2014 ' + story.title;
    // Update swatch line with story colour + dash pattern
    var swLine = swatchEl.querySelector('line');
    if (swLine) {
      swLine.setAttribute('stroke', story.colour);
      var dashMap = {dashed: '5,3', dotted: '2,3', bold: '', solid: ''};
      var da = dashMap[story.pattern] || '';
      swLine.setAttribute('stroke-dasharray', da);
      swLine.setAttribute('stroke-width', story.pattern === 'bold' ? '4' : '2.5');
    }

    document.querySelectorAll('.sidebar li a.explorer-active').forEach(function(a) {
      a.classList.remove('explorer-active');
    });
    var sidebar = document.querySelector('.sidebar');
    document.querySelectorAll('.sidebar li a').forEach(function(a) {
      if (a.textContent.indexOf(story.id + ':') === 0) {
        a.classList.add('explorer-active');
        // Open parent <details> if collapsed so the link is visible
        var det = a.closest('details');
        if (det && !det.open) det.open = true;
        // Scroll only the sidebar, not the page
        var aRect = a.getBoundingClientRect();
        var sRect = sidebar.getBoundingClientRect();
        if (aRect.top < sRect.top) {
          sidebar.scrollTop += aRect.top - sRect.top;
        } else if (aRect.bottom > sRect.bottom) {
          sidebar.scrollTop += aRect.bottom - sRect.bottom;
        }
      }
    });
  }

  // --- Keyboard ---
  document.addEventListener('keydown', function(e) {
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
    // Let browser shortcuts (Ctrl+L, Ctrl+H, etc.) pass through
    if (e.ctrlKey || e.metaKey) return;

    var cx = explorer.clientWidth / 2;
    var cy = explorer.clientHeight / 2;

    switch (e.key) {
      case 'ArrowRight':
      case 'l':
        e.preventDefault();
        if (storyIdx < STORIES.length - 1) {
          storyIdx++;
          highlightStory(storyIdx);
        }
        break;

      case 'ArrowLeft':
      case 'h':
        e.preventDefault();
        if (storyIdx > 0) {
          storyIdx--;
          highlightStory(storyIdx);
        } else if (storyIdx === 0) {
          storyIdx = -1;
          highlightStory(-1);
        }
        break;

      case 'Escape':
        e.preventDefault();
        storyIdx = -1;
        highlightStory(-1);
        break;

      case 'Enter':
        e.preventDefault();
        if (storyIdx >= 0 && storyIdx < STORIES.length) {
          window.location.href = STORIES[storyIdx].url;
        }
        break;

      case '=':
      case '+':
        e.preventDefault();
        zoom(ZOOM_STEP, cx, cy);
        break;

      case '-':
        e.preventDefault();
        zoom(-ZOOM_STEP, cx, cy);
        break;

      case '0':
        e.preventDefault();
        resetView();
        break;
    }
  });

  // --- Mouse wheel zoom ---
  explorer.addEventListener('wheel', function(e) {
    e.preventDefault();
    var rect = explorer.getBoundingClientRect();
    var cx = e.clientX - rect.left;
    var cy = e.clientY - rect.top;
    var delta = e.deltaY < 0 ? ZOOM_STEP : -ZOOM_STEP;
    zoom(delta, cx, cy);
  }, { passive: false });

  // --- Mouse drag pan ---
  explorer.addEventListener('mousedown', function(e) {
    if (e.button !== 0) return;
    dragging = true;
    dragStartX = e.clientX; dragStartY = e.clientY;
    panStartX = panX; panStartY = panY;
  });
  window.addEventListener('mousemove', function(e) {
    if (!dragging) return;
    panX = panStartX + (e.clientX - dragStartX);
    panY = panStartY + (e.clientY - dragStartY);
    applyTransform();
  });
  window.addEventListener('mouseup', function() { dragging = false; });

  // --- Click node -> select that story ---
  allNodes.forEach(function(node) {
    node.addEventListener('click', function(e) {
      var nid = node.getAttribute('data-node');
      if (!nid) return;
      for (var i = 0; i < STORIES.length; i++) {
        var ns = storyNodeSet(STORIES[i]);
        if (ns[nid]) {
          e.stopPropagation();
          storyIdx = i;
          highlightStory(i);
          return;
        }
      }
    });
  });

  // --- Sidebar link click -> highlight that story on DAG ---
  document.querySelectorAll('.sidebar li a').forEach(function(a) {
    a.addEventListener('click', function(e) {
      var text = a.textContent;
      for (var i = 0; i < STORIES.length; i++) {
        if (text.indexOf(STORIES[i].id + ':') === 0) {
          e.preventDefault();
          storyIdx = i;
          highlightStory(i);
          return;
        }
      }
    });
  });

  // --- Init ---
  resetView();

  // Start with US-3.5 highlighted (full chain, most intuitive)
  var defaultIdx = -1;
  for (var di = 0; di < STORIES.length; di++) {
    if (STORIES[di].id === 'US-3.5') { defaultIdx = di; break; }
  }
  if (defaultIdx >= 0) {
    storyIdx = defaultIdx;
    highlightStory(storyIdx);
  } else {
    statusEl.style.display = 'none';
  }

  hintsEl.innerHTML =
    '<kbd>&#x2190;</kbd><kbd>&#x2192;</kbd> cycle stories \u00b7 ' +
    '<kbd>Enter</kbd> open \u00b7 ' +
    '<kbd>Esc</kbd> overview \u00b7 ' +
    '<kbd>+</kbd><kbd>-</kbd> zoom \u00b7 ' +
    '<kbd>0</kbd> reset \u00b7 scroll to zoom \u00b7 drag to pan';
})();
"""


def generate_zoom_js() -> str:
    """Generate the zoom-pane JavaScript for independently zoomable regions.

    Each element with class ``zoom-pane`` becomes a zoomable region.
    Clicking selects it (highlighted outline).

    Two zoom modes:
    - Ctrl+/-: Coupled mode — grid columns rebalance proportionally.
    - , / . keys (or buttons): Independent mode — only the target pane
      changes width (in pixels). The other pane stays exactly the same
      size. / to reset.
    - Ctrl+0: Reset all.
    """
    return r"""
(function() {
  'use strict';
  var panes = document.querySelectorAll('.zoom-pane');
  if (!panes.length) return;

  var selected = null;
  var scaleMap = {};

  // Independent mode state per grid: stores pixel widths
  var indepWidths = new WeakMap();

  // Find the innermost zoom-pane for a given element
  function closestPane(el) {
    while (el) {
      if (el.classList && el.classList.contains('zoom-pane')
          && el.getAttribute('data-zoom-id')) {
        return el;
      }
      el = el.parentElement;
    }
    return null;
  }

  panes.forEach(function(pane) {
    var id = pane.getAttribute('data-zoom-id');
    if (!id) return;
    scaleMap[id] = 1;

    // Add zoom indicator
    var indicator = document.createElement('span');
    indicator.className = 'zoom-indicator';
    indicator.textContent = '100%';
    pane.appendChild(indicator);

    // Add resize buttons for panes inside a video-dag-row grid
    if (pane.closest('.video-dag-row')) {
      var btnGroup = document.createElement('span');
      btnGroup.className = 'zoom-resize-buttons';

      var btnShrink = document.createElement('button');
      btnShrink.className = 'zoom-resize-btn';
      btnShrink.textContent = '\u2212';
      btnShrink.title = 'Shrink this pane only';
      btnShrink.addEventListener('click', function(e) {
        e.stopPropagation();
        selectPane(pane);
        indepResize(pane, -1);
      });

      var btnGrow = document.createElement('button');
      btnGrow.className = 'zoom-resize-btn';
      btnGrow.textContent = '+';
      btnGrow.title = 'Grow this pane only';
      btnGrow.addEventListener('click', function(e) {
        e.stopPropagation();
        selectPane(pane);
        indepResize(pane, +1);
      });

      var btnReset = document.createElement('button');
      btnReset.className = 'zoom-resize-btn';
      btnReset.textContent = '\u21ba';
      btnReset.title = 'Reset pane size';
      btnReset.addEventListener('click', function(e) {
        e.stopPropagation();
        selectPane(pane);
        resetAll(pane);
      });

      btnGroup.appendChild(btnShrink);
      btnGroup.appendChild(btnGrow);
      btnGroup.appendChild(btnReset);
      pane.appendChild(btnGroup);
    }
  });

  // Single document-level listener picks the innermost zoom-pane
  document.addEventListener('mousedown', function(e) {
    var pane = closestPane(e.target);
    if (pane) selectPane(pane);
  });

  function selectPane(pane) {
    if (selected === pane) return;
    panes.forEach(function(p) { p.classList.remove('zoom-selected'); });
    pane.classList.add('zoom-selected');
    selected = pane;
  }

  function clearTransforms(pane) {
    var inner = pane.querySelector('.zoom-pane-inner');
    if (inner) {
      inner.style.transform = '';
      inner.style.transformOrigin = '';
      inner.style.width = '';
      inner.style.height = '';
    }
    pane.style.zoom = '';
  }

  function getIndicator(pane) {
    for (var j = 0; j < pane.children.length; j++) {
      if (pane.children[j].classList.contains('zoom-indicator')) {
        return pane.children[j];
      }
    }
    return null;
  }

  // Independent resize using pixel widths.
  // direction: -1 = shrink, +1 = grow
  var STEP_PX = 40;

  function indepResize(pane, direction) {
    var grid = pane.closest('.video-dag-row');
    if (!grid) return;

    var vp = grid.querySelector('.video-section.zoom-pane');
    var dp = grid.querySelector('.dag-section.zoom-pane');
    if (!vp || !dp) return;

    // Clear any coupled-mode zoom first
    clearTransforms(vp);
    clearTransforms(dp);
    scaleMap[vp.getAttribute('data-zoom-id')] = 1;
    scaleMap[dp.getAttribute('data-zoom-id')] = 1;

    // Snapshot current widths if not already in independent mode
    var w = indepWidths.get(grid);
    if (!w) {
      w = {
        video: vp.getBoundingClientRect().width,
        dag: dp.getBoundingClientRect().width
      };
      indepWidths.set(grid, w);
    }

    // Adjust only the target pane
    var isVideo = pane === vp;
    var key = isVideo ? 'video' : 'dag';
    w[key] = Math.max(100, w[key] + direction * STEP_PX);

    grid.style.gridTemplateColumns = w.video + 'px ' + w.dag + 'px';

    // Update indicators
    var vInd = getIndicator(vp);
    var dInd = getIndicator(dp);
    if (vInd) vInd.textContent = Math.round(w.video) + 'px';
    if (dInd) dInd.textContent = Math.round(w.dag) + 'px';
  }

  function resetAll(pane) {
    var grid = pane.closest('.video-dag-row');
    if (grid) {
      grid.style.gridTemplateColumns = '';
      indepWidths.delete(grid);
    }

    var vp = grid && grid.querySelector('.video-section.zoom-pane');
    var dp = grid && grid.querySelector('.dag-section.zoom-pane');

    if (vp) { clearTransforms(vp); scaleMap[vp.getAttribute('data-zoom-id')] = 1; }
    if (dp) { clearTransforms(dp); scaleMap[dp.getAttribute('data-zoom-id')] = 1; }

    var vInd = vp && getIndicator(vp);
    var dInd = dp && getIndicator(dp);
    if (vInd) vInd.textContent = '100%';
    if (dInd) dInd.textContent = '100%';
  }

  function applyCoupledZoom(pane) {
    var id = pane.getAttribute('data-zoom-id');
    var scale = scaleMap[id];

    var inner = pane.querySelector('.zoom-pane-inner');
    if (inner) {
      inner.style.transform = '';
      inner.style.transformOrigin = '';
      inner.style.width = '';
      inner.style.height = '';
    }
    pane.style.zoom = scale;

    var grid = pane.closest('.video-dag-row');
    if (grid) {
      indepWidths.delete(grid);
      var videoScale = 1, dagScale = 1;
      var vp = grid.querySelector('.video-section.zoom-pane');
      var dp = grid.querySelector('.dag-section.zoom-pane');
      if (vp) videoScale = scaleMap[vp.getAttribute('data-zoom-id')] || 1;
      if (dp) dagScale = scaleMap[dp.getAttribute('data-zoom-id')] || 1;
      grid.style.gridTemplateColumns = videoScale + 'fr ' + dagScale + 'fr';
    }
    var indicator = getIndicator(pane);
    if (indicator) {
      indicator.textContent = Math.round(scale * 100) + '%';
    }
  }

  // Ctrl+/- = coupled zoom
  document.addEventListener('keydown', function(e) {
    if (!selected) return;
    if (!e.ctrlKey && !e.metaKey) return;
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
    if (e.altKey || e.shiftKey) return;

    var id = selected.getAttribute('data-zoom-id');

    if (e.key === '=' || e.key === '+') {
      e.preventDefault();
      scaleMap[id] = Math.min(scaleMap[id] + 0.1, 3);
      applyCoupledZoom(selected);
    } else if (e.key === '-') {
      e.preventDefault();
      scaleMap[id] = Math.max(scaleMap[id] - 0.1, 0.3);
      applyCoupledZoom(selected);
    } else if (e.key === '0') {
      e.preventDefault();
      resetAll(selected);
    }
  });

  // Independent resize: , (or <) to shrink, . (or >) to grow, / to reset.
  // Also [ ] \ as alternatives.
  document.addEventListener('keydown', function(e) {
    if (!selected) return;
    if (e.ctrlKey || e.metaKey || e.altKey) return;
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
    if (e.target.tagName === 'BUTTON') return;

    var inGrid = !!selected.closest('.video-dag-row');
    if (!inGrid) return;

    if (e.key === ',' || e.key === '<' || e.key === '[') {
      e.preventDefault();
      indepResize(selected, -1);
    } else if (e.key === '.' || e.key === '>' || e.key === ']') {
      e.preventDefault();
      indepResize(selected, +1);
    } else if (e.key === '/' || e.key === '\\') {
      e.preventDefault();
      resetAll(selected);
    }
  });

  // Alt+Left/Right: cycle which pane is selected
  document.addEventListener('keydown', function(e) {
    if (!e.altKey) return;
    if (e.ctrlKey || e.metaKey) return;
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
    if (e.key !== 'ArrowLeft' && e.key !== 'ArrowRight') return;
    e.preventDefault();
    var arr = Array.prototype.slice.call(panes);
    if (!arr.length) return;
    var cur = selected ? arr.indexOf(selected) : -1;
    var next;
    if (e.key === 'ArrowRight') {
      next = (cur + 1) % arr.length;
    } else {
      next = (cur - 1 + arr.length) % arr.length;
    }
    selectPane(arr[next]);
    arr[next].scrollIntoView({behavior: 'smooth', block: 'nearest'});
  });

  // Mouse wheel zoom — Ctrl+scroll = coupled
  document.addEventListener('wheel', function(e) {
    if (!e.ctrlKey && !e.metaKey) return;
    var pane = closestPane(e.target);
    if (!pane) return;
    e.preventDefault();
    selectPane(pane);
    var id = pane.getAttribute('data-zoom-id');
    var delta = e.deltaY > 0 ? -0.1 : 0.1;
    scaleMap[id] = Math.max(0.3, Math.min(3, scaleMap[id] + delta));
    applyCoupledZoom(pane);
  }, {passive: false});
})();
"""


def _html_head(*, title: str) -> str:
    return f"""\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<link rel="stylesheet" href="{{CSS_PATH}}">
</head>
<body>
"""


def _line_swatch_svg(*, colour: str, pattern: str) -> str:
    """Return an inline SVG showing a short line with the story's colour and dash pattern."""
    dash_map = {"dashed": "5,3", "dotted": "2,3", "bold": "", "solid": ""}
    da = dash_map.get(pattern, "")
    sw = "3.5" if pattern == "bold" else "2"
    da_attr = f' stroke-dasharray="{da}"' if da else ""
    return (
        '<svg class="sidebar-swatch" viewBox="0 0 22 10"'
        ' style="width:22px;height:10px;vertical-align:middle;margin-right:4px;flex-shrink:0"><line'
        f' x1="1" y1="5" x2="21" y2="5" stroke="{colour}"'
        f' stroke-width="{sw}"{da_attr}/></svg>'
    )


def _sidebar_html(
    *,
    sections: "OrderedDict[str, List[Dict]]",
    current_story_id: Optional[str] = None,
    stories_with_video: Optional[set] = None,
) -> str:
    html = '<nav class="sidebar zoom-pane" data-zoom-id="sidebar">\n'
    html += '<div class="zoom-pane-inner">\n'
    html += '<h1><a href="{INDEX_PATH}">hledger-preprocessor</a></h1>\n'
    html += (
        '<p style="font-size:0.75rem;color:var(--text-muted);margin-bottom:1rem">'
    )
    html += "User Story DAG Explorer</p>\n"
    swv = stories_with_video or set()
    for section, stories in sections.items():
        is_current = current_story_id and any(
            s["id"] == current_story_id for s in stories
        )
        has_playable = any(s["id"] in swv for s in stories)
        open_attr = " open" if (is_current or has_playable) else ""
        html += f"<details{open_attr}>\n"
        html += f"<summary>{_esc(section)}</summary>\n<ul>\n"
        for s in stories:
            active = ' class="active"' if s["id"] == current_story_id else ""
            play_icon = " &#x25b6;" if s["id"] in swv else ""
            swatch = _line_swatch_svg(
                colour=s.get("colour", "#7aa2f7"),
                pattern=s.get("pattern", "solid"),
            )
            html += (
                f'<li><a href="{{STORIES_PATH}}/{s["id"]}.html"{active}'
                ' style="display:inline-flex;align-items:center">'
                f"{swatch}"
                f'{s["id"]}: {_esc(s["title"])}{play_icon}</a></li>\n'
            )
        html += "</ul>\n</details>\n"
    html += "</div>\n"  # close zoom-pane-inner
    html += "</nav>\n"
    return html


def generate_index_html(
    *,
    sections: "OrderedDict[str, List[Dict]]",
    overview_svg: Optional[str] = None,
    stories_json: str = "[]",
    stories_with_video: Optional[set] = None,
) -> str:
    head = _html_head(title="User Story DAG — hledger-preprocessor")
    head = head.replace("{CSS_PATH}", "assets/css/style.css")
    sidebar = _sidebar_html(
        sections=sections, stories_with_video=stories_with_video
    )
    sidebar = sidebar.replace("{INDEX_PATH}", "index.html")
    sidebar = sidebar.replace("{STORIES_PATH}", "stories")

    main = '<div class="main">\n'
    main += "<h1>User Story DAG</h1>\n"
    main += '<p style="margin-bottom:0.8rem;color:var(--text-muted)">'
    main += "Interactive explorer &mdash; use "
    main += '<kbd style="padding:0.1rem 0.35rem;background:var(--bg-card);'
    main += (
        'border:1px solid var(--border);border-radius:3px;font-size:0.8rem">'
    )
    main += "&#x2192;</kbd> to start cycling through stories."
    main += "</p>\n"

    if overview_svg:
        # Interactive zoomable SVG explorer
        main += '<div class="dag-explorer">\n'
        main += overview_svg + "\n"
        main += '<div class="explorer-status" id="explorer-status">\n'
        main += (
            '<svg class="story-line-swatch" id="explorer-swatch" viewBox="0 0'
            ' 32 14">'
        )
        main += (
            '<line x1="2" y1="7" x2="30" y2="7" stroke="#888"'
            ' stroke-width="2.5"/>'
        )
        main += "</svg>\n"
        main += '<span class="story-counter" id="explorer-counter"></span>\n'
        main += '<span class="story-title" id="explorer-title"></span>\n'
        main += '<span class="hints" id="explorer-hints"></span>\n'
        main += "</div>\n"
        main += "</div>\n"
    main += "</div>\n"

    # Embed story data and explorer JS
    js_block = (
        f"<script>\nconst STORIES = {stories_json};\n</script>\n"
        f'<script src="assets/js/dag-explorer.js"></script>\n'
        f'<script src="assets/js/zoom-pane.js"></script>\n'
    )

    return head + sidebar + main + js_block + "</body>\n</html>\n"


# ---------------------------------------------------------------------------
# Issue 3: Matching outcome flow diagram
# ---------------------------------------------------------------------------

# The matching algorithm retries in a loop.  Each outcome either terminates
# (match found / blocked / skipped) or loops back for another attempt.
_MATCHING_FLOW_OUTCOMES: List[Dict[str, str]] = [
    {"id": "out_auto_1hit", "short": "AUTO-LINK", "kind": "terminal"},
    {
        "id": "out_currency_convert",
        "short": "CURRENCY\nCONVERT",
        "kind": "terminal",
    },
    {
        "id": "out_currency_convert_fee",
        "short": "CURRENCY\n+ FEE",
        "kind": "terminal",
    },
    {"id": "out_widen_date", "short": "WIDEN\nDATE", "kind": "retry"},
    {"id": "out_widen_amount", "short": "WIDEN\nAMOUNT", "kind": "retry"},
    {"id": "out_swap_dd_mm", "short": "SWAP\nDD/MM", "kind": "retry"},
    {"id": "out_correct_receipt", "short": "CORRECT\nRECEIPT", "kind": "retry"},
    {"id": "out_disambiguate_3", "short": "DISAMBIGUATE", "kind": "terminal"},
    {"id": "out_too_many_reduce", "short": "TOO MANY\n(15+)", "kind": "retry"},
    {"id": "out_skip_cash", "short": "SKIP\n(cash)", "kind": "terminal"},
    {
        "id": "out_duplicate_blocked",
        "short": "BLOCKED\n(dup)",
        "kind": "terminal",
    },
    {"id": "out_asset_convert", "short": "ASSET\nCONVERT", "kind": "terminal"},
    {
        "id": "out_csv_only_classify",
        "short": "CLASSIFY\n(CSV)",
        "kind": "terminal",
    },
]


def generate_matching_flow_svg(
    *,
    highlight_outcome_ids: List[str],
    story_colour: str = "#4CAF50",
) -> str:
    """Return an inline SVG showing the matching retry flowchart.

    The flowchart has a central "Try to match" decision node.  Outcomes branch
    out — "retry" outcomes loop back to Try-to-match; "terminal" outcomes end
    the flow.  Nodes whose id is in *highlight_outcome_ids* are drawn with the
    story colour; all others are dimmed.
    """
    hl = set(highlight_outcome_ids)

    # Layout constants
    cx = 300  # centre-x of "Try to match" diamond
    cy = 60  # centre-y of diamond
    dw, dh = 140, 50  # diamond half-size
    box_w, box_h = 110, 46
    gap_y = 90  # vertical gap from diamond centre to outcome row
    retry_outcomes = [
        o for o in _MATCHING_FLOW_OUTCOMES if o["kind"] == "retry"
    ]
    terminal_outcomes = [
        o for o in _MATCHING_FLOW_OUTCOMES if o["kind"] == "terminal"
    ]

    # Place retry outcomes (top row, looping back)
    retry_x_start = 30
    retry_spacing = 130
    retry_y = cy + gap_y + 20

    # Place terminal outcomes (bottom row, no loop)
    term_y = retry_y + box_h + 80
    term_spacing = 110
    total_term_w = len(terminal_outcomes) * term_spacing
    term_x_start = max(20, cx - total_term_w // 2)

    svg_w = max(
        retry_x_start + len(retry_outcomes) * retry_spacing + 40,
        term_x_start + total_term_w + 40,
        660,
    )
    svg_h = term_y + box_h + 30

    lines: List[str] = []
    lines.append(
        '<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {svg_w} {svg_h}" '
        'style="max-width:100%;height:auto;font-family:system-ui,sans-serif;font-size:11px">'
    )
    lines.append("<defs>")
    lines.append(
        '<marker id="mf-arrow" markerWidth="8" markerHeight="6" '
        'refX="8" refY="3" orient="auto">'
        '<path d="M0,0 L8,3 L0,6 Z" fill="#555"/></marker>'
    )
    lines.append(
        '<marker id="mf-arrow-hl" markerWidth="8" markerHeight="6" '
        'refX="8" refY="3" orient="auto">'
        f'<path d="M0,0 L8,3 L0,6 Z" fill="{story_colour}"/></marker>'
    )
    lines.append("</defs>")

    # Diamond: "Try to match"
    diamond_pts = f"{cx},{cy - dh} {cx + dw},{cy} {cx},{cy + dh} {cx - dw},{cy}"
    lines.append(
        f'<polygon points="{diamond_pts}" '
        'fill="#e3f2fd" stroke="#1565c0" stroke-width="2"/>'
    )
    lines.append(
        f'<text x="{cx}" y="{cy - 6}" text-anchor="middle" '
        'font-weight="bold" font-size="13" fill="#1565c0">Try to</text>'
    )
    lines.append(
        f'<text x="{cx}" y="{cy + 10}" text-anchor="middle" '
        'font-weight="bold" font-size="13" fill="#1565c0">match</text>'
    )

    # Section labels
    lines.append(
        f'<text x="{cx}" y="{retry_y - 28}" text-anchor="middle" '
        'font-size="10" fill="#888" font-style="italic">'
        "retry outcomes (loop back)</text>"
    )
    lines.append(
        f'<text x="{cx}" y="{term_y - 12}" text-anchor="middle" '
        'font-size="10" fill="#888" font-style="italic">'
        "terminal outcomes (flow ends)</text>"
    )

    def _box(
        x: int,
        y: int,
        w: int,
        h: int,
        oid: str,
        label: str,
        is_hl: bool,
        kind: str,
    ) -> None:
        fill = "#fff" if not is_hl else "#e8f5e9"
        stroke = story_colour if is_hl else "#bbb"
        sw = "2.5" if is_hl else "1"
        opacity = "1" if is_hl else "0.55"
        rx = "8" if kind == "terminal" else "4"
        lines.append(
            f'<g opacity="{opacity}">'
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" '
            f'rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'
        )
        # Multi-line label
        label_lines = label.split("\n")
        if len(label_lines) == 1:
            ty = y + h // 2 + 4
            lines.append(
                f'<text x="{x + w // 2}" y="{ty}" text-anchor="middle" '
                f'font-size="10" fill="#333">{_esc(label_lines[0])}</text>'
            )
        else:
            ty = y + h // 2 - 4
            for li, lt in enumerate(label_lines):
                lines.append(
                    f'<text x="{x + w // 2}" y="{ty + li * 14}" '
                    'text-anchor="middle" font-size="10" fill="#333">'
                    f"{_esc(lt)}</text>"
                )
        lines.append("</g>")

    def _arrow(
        x1: int, y1: int, x2: int, y2: int, is_hl: bool, curved: bool = False
    ) -> None:
        stroke = story_colour if is_hl else "#999"
        sw = "2" if is_hl else "1"
        marker = "mf-arrow-hl" if is_hl else "mf-arrow"
        opacity = "1" if is_hl else "0.4"
        if curved:
            # S-curve from (x1,y1) to (x2,y2)
            mid_y = (y1 + y2) // 2
            lines.append(
                f'<path d="M{x1},{y1} C{x1},{mid_y} {x2},{mid_y} {x2},{y2}" '
                f'fill="none" stroke="{stroke}" stroke-width="{sw}" '
                f'opacity="{opacity}" marker-end="url(#{marker})"/>'
            )
        else:
            lines.append(
                f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
                f'stroke="{stroke}" stroke-width="{sw}" '
                f'opacity="{opacity}" marker-end="url(#{marker})"/>'
            )

    # Draw retry outcomes
    for idx, out in enumerate(retry_outcomes):
        bx = retry_x_start + idx * retry_spacing
        by = retry_y
        is_hl = out["id"] in hl
        _box(bx, by, box_w, box_h, out["id"], out["short"], is_hl, "retry")

        # Arrow from diamond down to box
        _arrow(cx, cy + dh, bx + box_w // 2, by, is_hl, curved=True)

        # Loop-back arrow from box top to diamond (curved up and back)
        lx = bx + box_w // 2
        loop_top = cy - dh - 25
        lines.append(
            f'<path d="M{lx},{by} L{lx},{loop_top} L{cx},{loop_top}" '
            f'fill="none" stroke="{"" + story_colour if is_hl else "#999"}" '
            f'stroke-width="{"2" if is_hl else "1"}" '
            'stroke-dasharray="4,3" '
            f'opacity="{"1" if is_hl else "0.35"}" '
            f'marker-end="url(#{"mf-arrow-hl" if is_hl else "mf-arrow"})"/>'
        )

    # Draw terminal outcomes
    for idx, out in enumerate(terminal_outcomes):
        bx = term_x_start + idx * term_spacing
        by = term_y
        is_hl = out["id"] in hl
        _box(
            bx,
            by,
            box_w - 10,
            box_h,
            out["id"],
            out["short"],
            is_hl,
            "terminal",
        )

        # Arrow from diamond down to box
        _arrow(cx, cy + dh, bx + (box_w - 10) // 2, by, is_hl, curved=True)

    lines.append("</svg>")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Issue 4: Journal output section
# ---------------------------------------------------------------------------

# Folder structure implied by the YAML directory paths
_JOURNAL_FOLDER_TEMPLATE = (
    "import/\n"
    "  {holder}/\n"
    "    {bank}/\n"
    "      {type}/\n"
    "        {year}/\n"
    "          {filename}.journal"
)

# Map account node IDs to human-readable account info
_ACCOUNT_FOLDER_INFO: Dict[str, Dict[str, str]] = {
    "acct_triodos_csv": {
        "holder": "john",
        "bank": "triodos",
        "type": "checking",
        "filename": "triodos-checking",
    },
    "acct_ing_csv": {
        "holder": "john",
        "bank": "ing",
        "type": "checking",
        "filename": "ing-checking",
    },
    "acct_eur_wallet": {
        "holder": "john",
        "bank": "wallet",
        "type": "eur",
        "filename": "eur-wallet",
    },
    "acct_gbp_wallet": {
        "holder": "john",
        "bank": "wallet",
        "type": "gbp",
        "filename": "gbp-wallet",
    },
    "acct_btc_wallet": {
        "holder": "john",
        "bank": "wallet",
        "type": "btc",
        "filename": "btc-wallet",
    },
    "acct_gold_wallet": {
        "holder": "john",
        "bank": "wallet",
        "type": "gold",
        "filename": "gold-wallet",
    },
    "acct_silver_wallet": {
        "holder": "john",
        "bank": "wallet",
        "type": "silver",
        "filename": "silver-wallet",
    },
}


def generate_journal_section(
    *,
    story: Dict,
    node_path: List[str],
    node_index: Dict[str, Dict],
) -> Optional[str]:
    """Return HTML for the journal output section, or None if N/A.

    Shows:
    1. A folder-tree view of the .journal directory structure
    2. The journal posting content for this story's journal nodes
    """
    # Find journal nodes in this story's path
    jrnl_nodes = [nid for nid in node_path if nid.startswith("jrnl_")]
    if not jrnl_nodes:
        return None

    # Find account nodes to determine folder structure
    acct_nodes = [nid for nid in node_path if nid.startswith("acct_")]

    html = '<div class="journal-output-section">\n'
    html += "<h2>Journal Output</h2>\n"

    # 1. Folder tree
    if acct_nodes:
        html += '<div class="journal-folder-tree">\n'
        html += "<h3>Folder Structure</h3>\n"
        html += "<pre><code>"
        # Show the year as 2024 (from start_2024 opening balance nodes)
        year = "2024"
        tree_lines: List[str] = ["import/"]
        # Group accounts by holder
        for acct_id in acct_nodes:
            info = _ACCOUNT_FOLDER_INFO.get(acct_id)
            if info:
                tree_lines.append(f"  {info['holder']}/")
                tree_lines.append(f"    {info['bank']}/")
                tree_lines.append(f"      {info['type']}/")
                tree_lines.append(f"        {year}/")
                tree_lines.append(f"          {info['filename']}.journal")
        # De-duplicate while preserving order for the tree display
        seen: set = set()
        deduped: List[str] = []
        for line in tree_lines:
            if line not in seen:
                seen.add(line)
                deduped.append(line)
        html += _esc("\n".join(deduped))
        html += "</code></pre>\n"
        html += "</div>\n"

    # 2. Journal postings
    html += '<div class="journal-postings">\n'
    html += "<h3>Journal Postings</h3>\n"
    for jnid in jrnl_nodes:
        ninfo = node_index.get(jnid, {})
        label = ninfo.get("label", jnid).replace("\n", " ")
        desc = ninfo.get("desc", "")
        html += '<div class="journal-entry">\n'
        html += f'<div class="journal-entry-header">{_esc(label)}</div>\n'
        # Build a simple hledger-style posting from the label
        posting = _build_journal_posting(label=label, desc=desc)
        if posting:
            html += f"<pre><code>{_esc(posting)}</code></pre>\n"
        html += "</div>\n"
    html += "</div>\n"

    html += "</div>\n"
    return html


def _build_journal_posting(*, label: str, desc: str) -> str:
    """Build a minimal hledger journal posting from a node label + desc."""
    # Label format: "Account:Sub: Description AMOUNT CURRENCY"
    # or "Account:Sub AMOUNT CURRENCY"
    # Desc provides context: "Debit X, credit Y" etc.
    clean = label.replace("\n", " ").strip()

    # Try to parse "Account:Path Amount Currency" from the label
    # Examples: "Expenses:Groceries: Ekoplaza 42.17 EUR"
    #           "Assets:Wallet: GBP 100"
    #           "Income:Salary 3000 EUR"
    parts = clean.split()
    if len(parts) < 2:
        return ""

    # Find the account part (contains ':')
    acct_parts: List[str] = []
    rest_parts: List[str] = []
    found_amount = False
    for p in parts:
        if not found_amount and ":" in p:
            acct_parts.append(p)
        elif not found_amount and not any(c.isdigit() for c in p):
            acct_parts.append(p)
        else:
            found_amount = True
            rest_parts.append(p)

    account = " ".join(acct_parts).rstrip(":")
    amount_str = " ".join(rest_parts)

    if not account or not amount_str:
        return f"; {clean}"

    # Build a 2-line posting
    date = "2025-01-15"  # representative date from the demo data
    posting = f"{date} {_desc_to_payee(desc=desc)}\n"
    posting += f"    {account}    {amount_str}\n"

    # Add the counter-posting from the desc
    counter = _desc_to_counter_account(desc=desc)
    if counter:
        posting += f"    {counter}"

    return posting


def _desc_to_payee(*, desc: str) -> str:
    """Extract a short payee name from a node description."""
    desc_lower = desc.lower()
    if "groceries" in desc_lower or "ekoplaza" in desc_lower:
        return "Ekoplaza groceries"
    if "withdrawal" in desc_lower or "atm" in desc_lower:
        return "ATM withdrawal"
    if "salary" in desc_lower or "income" in desc_lower:
        return "Salary deposit"
    if "dinner" in desc_lower or "restaurant" in desc_lower:
        return "Restaurant dinner"
    if "coffee" in desc_lower:
        return "Coffee purchase"
    if "bike" in desc_lower or "repair" in desc_lower:
        return "Bike repair"
    if "gold" in desc_lower:
        return "Gold purchase"
    if "rent" in desc_lower:
        return "Rent payment"
    if "return" in desc_lower:
        return "Shopping (with return)"
    if "bank" in desc_lower and "fee" in desc_lower:
        return "Bank fee"
    if "delayed" in desc_lower:
        return "Delayed shop purchase"
    if "rounded" in desc_lower:
        return "Shop purchase (rounded)"
    if "swapped" in desc_lower or "dd/mm" in desc_lower:
        return "Shop purchase (date fix)"
    return "Transaction"


def _desc_to_counter_account(*, desc: str) -> str:
    """Derive the counter-posting account from a node description."""
    d = desc.lower()
    if "credit triodos" in d or "debit triodos" in d:
        return "Assets:Triodos:Checking"
    if "credit eur wallet" in d or "credit eur" in d:
        return "Assets:Wallet:EUR"
    if "credit ing" in d:
        return "Assets:ING:Checking"
    if "debit groceries" in d:
        return "Assets:Triodos:Checking"
    if "debit dining" in d:
        return "Assets:Wallet:EUR"
    if "debit repairs" in d:
        return "Assets:Wallet:EUR"
    if "debit income" in d or "credit income" in d:
        return "Assets:Triodos:Checking"
    if "bank debit" in d:
        return ""  # already specified in the posting
    return ""


def generate_story_html(
    *,
    story: Dict,
    sections: "OrderedDict[str, List[Dict]]",
    prev_story: Optional[Dict],
    next_story: Optional[Dict],
    video_filename: Optional[str],
    is_gif: bool,
    svg_content: Optional[str],
    has_png_fallback: bool,
    timestamps: Dict[str, float],
    node_path: List[str],
    node_index: Dict[str, Dict],
    filtered_components_map: Optional[Dict[str, List[Dict]]] = None,
    stories_with_video: Optional[set] = None,
    receipt_image: Optional[str] = None,
    full_svg_content: Optional[str] = None,
    matching_flow_svg: Optional[str] = None,
    journal_section_html: Optional[str] = None,
) -> str:
    sid = story["id"]
    head = _html_head(title=f"{sid}: {story['title']} — hledger-preprocessor")
    head = head.replace("{CSS_PATH}", "../assets/css/style.css")
    sidebar = _sidebar_html(
        sections=sections,
        current_story_id=sid,
        stories_with_video=stories_with_video,
    )
    sidebar = sidebar.replace("{INDEX_PATH}", "../index.html")
    sidebar = sidebar.replace("{STORIES_PATH}", ".")

    colour = story.get("colour", "#7aa2f7")
    status = story.get("status")
    badge = ""
    if status == "NOT YET IMPLEMENTED":
        badge = '<span class="badge badge-not-impl">not implemented</span>'
    elif status == "WONTFIX":
        badge = '<span class="badge badge-wontfix">wontfix</span>'
    elif status is None or status == "IMPL":
        badge = '<span class="badge badge-impl">implemented</span>'

    main = '<div class="main zoom-pane" data-zoom-id="content">\n'
    main += '<div class="zoom-pane-inner">\n'

    # -- Navigation hints bar (Issue v6-A) --
    main += '<div class="nav-hints">\n'
    main += (
        "<span><kbd>Alt</kbd>+<kbd>&#x2190;</kbd><kbd>&#x2192;</kbd> cycle"
        " focus</span>\n"
    )
    main += (
        "<span><kbd>&#x2191;</kbd><kbd>&#x2193;</kbd> /"
        " <kbd>j</kbd><kbd>k</kbd> prev/next DAG node</span>\n"
    )
    main += (
        "<span><kbd>Ctrl</kbd>+<kbd>+</kbd><kbd>−</kbd> zoom focused"
        " pane</span>\n"
    )
    main += (
        "<span><kbd>,</kbd><kbd>.</kbd> resize pane only &middot; <kbd>/</kbd>"
        " reset</span>\n"
    )
    main += "<span><kbd>Ctrl</kbd>+<kbd>0</kbd> reset zoom</span>\n"
    main += "<span><kbd>Space</kbd> play/pause</span>\n"
    main += "</div>\n"

    # -- Compact story header with receipt image floated left --
    main += f'<div class="story-header" style="border-left-color:{colour}">\n'

    if receipt_image:
        # Receipt image in its own zoom pane, floated left.
        # SVG overlay provides bounding boxes for field highlighting.
        # Boxes are loaded from a sidecar *_boxes.json generated by
        # gifs/automation/receipt_renderer.py alongside each receipt PNG.
        receipt_overlay = ""
        stem = Path(receipt_image).stem
        boxes_path = RECEIPTS_ROOT / f"{stem}_boxes.json"
        if boxes_path.exists():
            boxes_data = json.loads(boxes_path.read_text())
            img_w = boxes_data["image_width"]
            img_h = boxes_data["image_height"]
            rects: List[str] = []
            for field_name, box_list in boxes_data["fields"].items():
                for box in box_list:
                    rects.append(
                        f'<rect data-field="{_esc(field_name)}" '
                        f'x="{box["x"]}" y="{box["y"]}" '
                        f'width="{box["w"]}" height="{box["h"]}" rx="2"/>'
                    )
            receipt_overlay = (
                f'<svg class="receipt-overlay" '
                f'viewBox="0 0 {img_w} {img_h}"'
                f' preserveAspectRatio="xMidYMid meet">\n'
                + "\n".join(rects)
                + "\n</svg>\n"
            )
        main += (
            '<div class="receipt-pane zoom-pane" data-zoom-id="receipt">\n'
            '<div class="zoom-pane-inner">\n'
            '<img class="receipt-image-inline" '
            f'src="../assets/receipts/{_esc(receipt_image)}" '
            f'alt="Receipt: {_esc(story["title"])}">\n'
            f'{receipt_overlay}'
            "</div></div>\n"
        )

    main += f'<span class="story-id">{_esc(sid)}{badge}</span> '
    main += f'<span class="story-title-inline">{_esc(story["title"])}</span>\n'

    # BDD narrative — compact single-block, text wraps to the right of receipt
    as_a = story.get("as_a", "")
    i_want = story.get("i_want", "")
    so_that = story.get("so_that", "")
    if as_a or i_want or so_that:
        main += '<div class="bdd-compact">\n'
        if as_a:
            main += f'<span class="bdd-kw">As a</span> {_esc(as_a)} '
        if i_want:
            main += f'<span class="bdd-kw">I want</span> {_esc(i_want)} '
        if so_that:
            main += f'<span class="bdd-kw">so that</span> {_esc(so_that)}'
        main += "\n</div>\n"

    main += '<div style="clear:both"></div>\n'
    main += "</div>\n"
    # (Acceptance criteria removed from page view per Issue 2)

    # Side-by-side video + DAG grid
    main += '<div class="video-dag-row">\n'

    # Video section (left column) — wrapped in zoom pane
    main += '<div class="video-section zoom-pane" data-zoom-id="video">\n'
    main += '<div class="zoom-pane-inner">\n'
    if video_filename:
        if is_gif:
            main += (
                f'<img src="../assets/videos/{video_filename}" '
                f'alt="Demo: {_esc(story["title"])}">\n'
            )
        else:
            main += (
                '<video id="demo-video" controls loop preload="metadata">\n'
                f'<source src="../assets/videos/{video_filename}" '
                'type="video/mp4">\n'
                "</video>\n"
            )
        main += '<div class="video-hint">'
        main += "&#x2191;&#x2193; arrows or j/k to jump between DAG nodes "
        main += "&middot; click a node to seek &middot; space to play/pause"
        main += "</div>\n"
    else:
        main += '<div class="coming-soon">Demo video coming soon</div>\n'
    main += "</div>\n"  # close zoom-pane-inner
    main += "</div>\n"  # close video-section zoom-pane

    # DAG diagram (right column, spans rows) — wrapped in zoom pane
    main += '<div class="dag-section zoom-pane" data-zoom-id="dag">\n'
    main += '<div class="zoom-pane-inner">\n'
    has_both_views = bool(svg_content and full_svg_content)
    if has_both_views:
        main += '<div class="dag-header">\n'
        main += "<h2>DAG Diagram</h2>\n"
        main += '<div class="dag-view-toggle">\n'
        main += (
            '<button id="btn-segment-view" class="toggle-btn active"'
            ' title="Show only this story\'s segment">'
            "Segment</button>\n"
        )
        main += (
            '<button id="btn-full-view" class="toggle-btn"'
            ' title="Show full end-to-end path">'
            "Full path</button>\n"
        )
        main += "</div>\n"
        main += "</div>\n"
    else:
        main += "<h2>DAG Diagram</h2>\n"

    if svg_content:
        main += f'<div id="dag-segment-view">\n{svg_content}\n</div>\n'
    elif has_png_fallback:
        safe = story_id_to_safe(story_id=sid)
        main += (
            '<div id="dag-segment-view">\n'
            '<img class="dag-fallback-img" '
            f'src="../assets/images/isolated/{safe}.png" '
            f'alt="DAG for {_esc(sid)}">\n'
            "</div>\n"
        )
    if full_svg_content:
        main += (
            '<div id="dag-full-view" style="display:none">\n'
            f"{full_svg_content}\n</div>\n"
        )
    main += "</div>\n"  # close zoom-pane-inner
    main += "</div>\n"  # close dag-section zoom-pane

    # Below-row: layer indicator
    main += '<div class="below-row">\n'
    if timestamps:
        main += '<div class="layer-indicator">\n'
        main += '<span class="layer-dot"></span>\n'
        main += (
            'Current layer: <span class="layer-name"'
            ' id="layer-indicator-name">—</span>\n'
        )
        main += "</div>\n"
    main += "</div>\n"  # close below-row
    main += "</div>\n"  # close video-dag-row

    # Issue 3: Matching outcome flow diagram (Step 3 stories)
    if matching_flow_svg:
        main += '<div class="matching-flow-section">\n'
        main += "<h2>Matching Flow</h2>\n"
        main += '<p class="matching-flow-desc">'
        main += (
            "The matching algorithm tries to find a CSV transaction for each "
        )
        main += (
            "receipt. Retry outcomes loop back for another attempt; terminal "
        )
        main += "outcomes end the flow."
        main += "</p>\n"
        main += matching_flow_svg + "\n"
        main += "</div>\n"

    # (Issue 4: Journal output removed from page view per ui-issues_v5)

    # Prev / Next
    main += '<div class="nav-links">\n'
    if prev_story:
        main += f'<a href="{prev_story["id"]}.html">← {prev_story["id"]}</a>\n'
    else:
        main += "<span></span>\n"
    if next_story:
        main += f'<a href="{next_story["id"]}.html">{next_story["id"]} →</a>\n'
    else:
        main += "<span></span>\n"
    main += "</div>\n"
    main += "</div>\n"  # close zoom-pane-inner
    main += "</div>\n"  # close main zoom-pane

    # Timestamp manifest + JS
    ts_json = json.dumps(timestamps)
    js_block = (
        f"<script>\nconst TIMESTAMPS = {ts_json};\n</script>\n"
        f'<script src="../assets/js/dag-sync.js"></script>\n'
        f'<script src="../assets/js/zoom-pane.js"></script>\n'
    )

    return head + sidebar + main + js_block + "</body>\n</html>\n"


def _esc(text: str) -> str:
    """Escape HTML special characters."""
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


# ---------------------------------------------------------------------------
# Asset copying
# ---------------------------------------------------------------------------
def copy_assets(
    *,
    output_dir: Path,
    video_map: Dict[str, Path],
    all_videos: Dict[str, Dict[str, Path]],
    sections: "OrderedDict[str, List[Dict]]",
    dim_opacity: Optional[float] = None,
) -> None:
    """Copy images and videos into the output directory."""
    img_dir = output_dir / "assets" / "images"
    iso_dir = img_dir / "isolated"
    vid_dir = output_dir / "assets" / "videos"
    css_dir = output_dir / "assets" / "css"
    js_dir = output_dir / "assets" / "js"
    stories_dir = output_dir / "stories"

    for d in [img_dir, iso_dir, vid_dir, css_dir, js_dir, stories_dir]:
        d.mkdir(parents=True, exist_ok=True)

    # Copy isolated PNGs
    iso_src = SCRIPT_DIR / "output" / "isolated"
    if iso_src.is_dir():
        for png in iso_src.glob("*.png"):
            shutil.copy2(png, iso_dir / png.name)

    # Copy all per-story videos
    copied: set = set()
    for _dir_name, stem_map in all_videos.items():
        for _stem, vid_path in stem_map.items():
            if vid_path.name not in copied:
                shutil.copy2(vid_path, vid_dir / vid_path.name)
                copied.add(vid_path.name)

    # Also copy section-level videos (for sections without per-story GIFs)
    for section in sections:
        vid = get_video_for_section(section=section, video_map=video_map)
        if vid and vid.name not in copied:
            shutil.copy2(vid, vid_dir / vid.name)
            copied.add(vid.name)

    # Copy receipt images
    receipt_dir = output_dir / "assets" / "receipts"
    receipt_dir.mkdir(parents=True, exist_ok=True)
    if RECEIPTS_ROOT.is_dir():
        for img_file in RECEIPTS_ROOT.iterdir():
            if img_file.suffix.lower() in (".png", ".jpg", ".jpeg"):
                shutil.copy2(img_file, receipt_dir / img_file.name)

    # Write CSS and JS
    (css_dir / "style.css").write_text(generate_css(dim_opacity=dim_opacity))
    (js_dir / "dag-sync.js").write_text(generate_js())
    (js_dir / "dag-explorer.js").write_text(generate_explorer_js())
    (js_dir / "zoom-pane.js").write_text(generate_zoom_js())


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate GitHub Pages site for user story DAG."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=OUTPUT_DIR_DEFAULT,
        help="Output directory (default: user_stories/dag/site/)",
    )
    parser.add_argument(
        "--no-svg",
        action="store_true",
        help="Skip PlantUML SVG generation, use PNG fallbacks",
    )
    parser.add_argument(
        "--dim-opacity",
        type=float,
        default=None,
        help=(
            "Opacity for non-used/unreachable DAG nodes (0.0–1.0, default:"
            " 0.18)"
        ),
    )
    args = parser.parse_args()
    output_dir = args.output

    print(f"Loading data from {DATA_FILE}...")
    data = load_data()
    all_stories = data.get("stories", [])
    stories = dag_stories(stories=all_stories)
    node_index = build_node_index(data=data)
    sections = group_stories_by_section(stories=stories)

    print(
        f"Found {len(stories)} stories with DAG paths in"
        f" {len(sections)} sections."
    )

    # Discover videos, cast files, and sidecar marker JSON files
    video_map = discover_videos(gifs_root=GIFS_ROOT, theme=DEFAULT_THEME)
    all_videos = discover_all_videos(gifs_root=GIFS_ROOT)
    cast_map = discover_cast_files(gifs_root=GIFS_ROOT)
    marker_json_map = discover_marker_json_files(gifs_root=GIFS_ROOT)
    total_videos = sum(len(v) for v in all_videos.values())
    total_markers = sum(len(v) for v in marker_json_map.values())
    print(
        f"Found {len(video_map)} video dirs ({total_videos} videos), "
        f"{len(cast_map)} cast files, "
        f"{total_markers} marker JSON files."
    )

    # Pre-compute which stories have videos
    stories_with_video: set = set()
    for s in stories:
        section = s.get("section", "")
        vid = get_video_for_story(
            story=s,
            section=section,
            video_map=video_map,
            all_videos=all_videos,
        )
        if vid:
            stories_with_video.add(s["id"])

    # Copy assets
    print(f"Copying assets to {output_dir}...")
    copy_assets(
        output_dir=output_dir,
        video_map=video_map,
        all_videos=all_videos,
        sections=sections,
        dim_opacity=args.dim_opacity,
    )

    # Generate SVGs (or skip)
    svg_cache: Dict[str, Optional[str]] = {}
    if not args.no_svg:
        print("Generating SVG diagrams...")
        for s in stories:
            safe = story_id_to_safe(story_id=s["id"])
            puml_path = SCRIPT_DIR / "output" / "isolated" / f"{safe}.puml"
            if puml_path.exists() and safe not in svg_cache:
                svg = generate_svg(puml_path=puml_path)
                if svg:
                    svg = add_data_attributes_to_svg(
                        svg=svg, node_index=node_index
                    )
                svg_cache[safe] = svg
        print(f"  Generated {sum(1 for v in svg_cache.values() if v)} SVGs.")

    # Generate overview SVG for the interactive explorer (direct, no Graphviz)
    overview_svg: Optional[str] = None
    if not args.no_svg:
        print("Generating overview SVG...")
        overview_svg = generate_overview_svg_direct(
            data=data, node_index=node_index, stories=stories
        )
        print("  Overview SVG ready.")

    # Build stories JSON for the explorer
    stories_for_json = []
    for s in stories:
        stories_for_json.append(
            {
                "id": s["id"],
                "title": s.get("title", ""),
                "colour": s.get("colour", "#7aa2f7"),
                "pattern": s.get("pattern", "solid"),
                "paths": s.get("paths", []),
                "url": f"stories/{s['id']}.html",
            }
        )
    stories_json = json.dumps(stories_for_json)

    # Generate index.html
    print("Generating index.html...")
    index_html = generate_index_html(
        sections=sections,
        overview_svg=overview_svg,
        stories_json=stories_json,
        stories_with_video=stories_with_video,
    )
    (output_dir / "index.html").write_text(index_html)

    # Generate per-story pages
    print("Generating story pages...")
    flat = list(stories)
    for i, story in enumerate(flat):
        prev_s = flat[i - 1] if i > 0 else None
        next_s = flat[i + 1] if i < len(flat) - 1 else None
        section = story.get("section", "")

        # Video: prefer per-story video (gif_video), fall back to section
        vid = get_video_for_story(
            story=story,
            section=section,
            video_map=video_map,
            all_videos=all_videos,
        )
        video_filename = vid.name if vid else None
        is_gif = video_filename.endswith(".gif") if video_filename else False

        # Node path — union of all paths (preserving order from path[0],
        # then appending any extra nodes from subsequent paths)
        all_paths = story.get("paths", [])
        seen_nodes: set = set()
        node_path: List[str] = []
        for p in all_paths:
            for nid in p:
                if nid not in seen_nodes:
                    seen_nodes.add(nid)
                    node_path.append(nid)

        # YAML-driven marker sequence (node + sub-component interleaved)
        marker_sequence = get_marker_sequence(
            story=story, node_index=node_index
        )

        # Check per-story sidecar marker JSON first, then fall back to
        # .cast @@NODE markers
        raw_markers: Dict[str, float] = get_markers_for_story(
            story=story,
            section=section,
            marker_json_map=marker_json_map,
        )
        if not raw_markers:
            raw_markers = get_node_markers_for_section(
                section=section, cast_map=cast_map
            )

        # Build timestamps using YAML ordering, populated from markers
        timestamps: Dict[str, float] = {}
        for marker_id in marker_sequence:
            if marker_id in raw_markers:
                timestamps[marker_id] = raw_markers[marker_id]

        # Include sub-component markers from sidecar JSON that weren't in the
        # YAML marker sequence (e.g. TUI field markers like tui_*__date).
        # These are dynamically generated by TUI demos and need to appear in
        # the TIMESTAMPS JS object for receipt-field highlighting.
        for marker_id, ts in raw_markers.items():
            if "__" in marker_id and marker_id not in timestamps:
                timestamps[marker_id] = ts

        # Infer missing parent-node timestamps from their first child.
        # Sidecar JSON may only contain sub-component keys (e.g.
        # cat_basic__groceries) without the parent (cat_basic).  If the parent
        # appears in the marker sequence but has no timestamp, set it to
        # the minimum timestamp of its children.
        for marker_id in marker_sequence:
            if "__" not in marker_id and marker_id not in timestamps:
                prefix = marker_id + "__"
                child_ts = [
                    timestamps[k] for k in timestamps if k.startswith(prefix)
                ]
                if child_ts:
                    timestamps[marker_id] = min(child_ts)

        # If no marker-derived timestamps, interpolate evenly across the
        # cast file duration (or fall back to 2s spacing).
        if not timestamps and marker_sequence:
            cast_dur = get_cast_duration_for_section(
                section=section, cast_map=cast_map
            )
            n = len(marker_sequence)
            step = (cast_dur / n) if cast_dur and n > 1 else 2.0
            for idx_m, mid in enumerate(marker_sequence):
                timestamps[mid] = round(idx_m * step, 2)

        # Full-path nodes that appear in paths but not in demo_paths may
        # have real timestamps in raw_markers (from the stitched video's
        # sidecar JSON).  Use those first before falling back to synthetic.
        missing_nodes = [
            nid
            for nid in node_path
            if nid not in timestamps and "__" not in nid
        ]
        for nid in list(missing_nodes):
            if nid in raw_markers:
                timestamps[nid] = raw_markers[nid]
                missing_nodes.remove(nid)
        # Remaining nodes with no marker data get synthetic timestamps
        # at evenly-spaced intervals after the last real marker.
        if missing_nodes and timestamps:
            last_ts = max(timestamps.values())
            step = 2.0  # 2-second spacing for synthetic timestamps
            for idx_m, nid in enumerate(missing_nodes, start=1):
                timestamps[nid] = round(last_ts + idx_m * step, 2)

        # Build per-node filtered component map from YAML component_filter
        filtered_components_map: Dict[str, List[Dict]] = {}
        for nid in node_path:
            filtered_components_map[nid] = get_filtered_components(
                story=story, node_id=nid, node_index=node_index
            )

        # SVG — generate per-story segment and full-path SVGs directly
        safe = story_id_to_safe(story_id=story["id"])
        has_png = (
            output_dir / "assets" / "images" / "isolated" / f"{safe}.png"
        ).exists()

        segment_svg: Optional[str] = None
        full_path_svg: Optional[str] = None
        colour = story.get("colour", "#7aa2f7")

        if not args.no_svg:
            # Segment view: only segment_nodes
            seg_nodes = story.get("segment_nodes", [])
            if seg_nodes:
                segment_svg = generate_story_svg_direct(
                    node_ids=seg_nodes,
                    node_index=node_index,
                    paths=all_paths,
                    story_colour=colour,
                    svg_id_prefix="seg_",
                )

            # Full-path view: all nodes from paths, with section-layer highlight
            section_layers = SECTION_PRIMARY_LAYERS.get(section, [])
            if node_path:
                full_path_svg = generate_story_svg_direct(
                    node_ids=node_path,
                    node_index=node_index,
                    paths=all_paths,
                    story_colour=colour,
                    highlight_layers=section_layers,
                    svg_id_prefix="fp_",
                )

        # Receipt image (from YAML receipt_image field)
        receipt_img = story.get("receipt_image")
        if receipt_img and not (RECEIPTS_ROOT / receipt_img).exists():
            receipt_img = None  # skip if image file doesn't exist

        # Issue 3: Matching flow diagram for stories with matching outcomes
        matching_flow: Optional[str] = None
        outcome_ids = [nid for nid in node_path if nid.startswith("out_")]
        if outcome_ids:
            matching_flow = generate_matching_flow_svg(
                highlight_outcome_ids=outcome_ids,
                story_colour=colour,
            )

        # Issue 4 (v5): Journal output removed from story page view.
        # The journal section generation is skipped; the data will be
        # included at another time via the GIF demo.

        story_html = generate_story_html(
            story=story,
            sections=sections,
            prev_story=prev_s,
            next_story=next_s,
            video_filename=video_filename,
            is_gif=is_gif,
            svg_content=segment_svg,
            has_png_fallback=has_png,
            timestamps=timestamps,
            node_path=node_path,
            node_index=node_index,
            filtered_components_map=filtered_components_map,
            stories_with_video=stories_with_video,
            receipt_image=receipt_img,
            full_svg_content=full_path_svg,
            matching_flow_svg=matching_flow,
        )
        (output_dir / "stories" / f"{story['id']}.html").write_text(story_html)

    print(f"Done! Site generated at {output_dir}/")
    print(f"  {len(flat)} story pages + index.html")
    print(f"  Open {output_dir}/index.html in a browser to preview.")


if __name__ == "__main__":
    main()
