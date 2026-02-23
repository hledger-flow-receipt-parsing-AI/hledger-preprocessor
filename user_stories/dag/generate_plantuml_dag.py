#!/usr/bin/env python3
"""Generate PlantUML DAG diagrams from user story data.

Reads userstory_dag_data.yaml and produces .puml files showing data-flow
paths through the test/demo fixture layers.

Usage:
    python generate_plantuml_dag.py --all                  # all stories overlaid
    python generate_plantuml_dag.py --story US-3.2         # single story isolated
    python generate_plantuml_dag.py --story US-3.2 --context full  # highlighted on full graph
    python generate_plantuml_dag.py --each                 # one file per story
    python generate_plantuml_dag.py --filter demo          # only demo data paths
    python generate_plantuml_dag.py --filter test           # only test data paths
    python generate_plantuml_dag.py --cli --story US-3.2   # ASCII box-drawing variant
    python generate_plantuml_dag.py --render               # also run plantuml to produce PNGs
"""

import argparse
import os
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import yaml

SCRIPT_DIR = Path(__file__).parent
DATA_FILE = SCRIPT_DIR / "userstory_dag_data.yaml"
OUTPUT_DIR = SCRIPT_DIR / "output"

# PlantUML layer colours (background fills for subgraph clusters)
LAYER_COLOURS = {
    "config": "#E3F2FD",
    "categories": "#E8F5E9",
    "matching_cfg": "#FFF3E0",
    "start_journal": "#F3E5F5",
    "csv_txn": "#E0F7FA",
    "receipt_img": "#FBE9E7",
    "receipt_lbl": "#FCE4EC",
    "matching_out": "#FFF8E1",
    "journal_out": "#E8EAF6",
    "visualization": "#F3E5F5",
}

LAYER_ORDER = [
    "config",
    "categories",
    "matching_cfg",
    "start_journal",
    "csv_txn",
    "receipt_img",
    "receipt_lbl",
    "matching_out",
    "journal_out",
    "visualization",
]


def load_data() -> Dict[str, Any]:
    with open(DATA_FILE) as f:
        return yaml.safe_load(f)


def build_node_index(data: Dict) -> Dict[str, Dict]:
    """Map node id -> {layer, label, desc, used_by}."""
    index = {}
    for layer in data["layers"]:
        for node in layer["nodes"]:
            index[node["id"]] = {
                "layer": layer["name"],
                "layer_label": layer["label"],
                "label": node["label"],
                "desc": node["desc"],
                "used_by": node.get("used_by", ["test"]),
            }
    return index


def collect_edges_from_paths(
    paths: List[List[str]],
) -> Set[Tuple[str, str]]:
    """Extract directed edges from a list of paths."""
    edges = set()
    for path in paths:
        for i in range(len(path) - 1):
            edges.add((path[i], path[i + 1]))
    return edges


def collect_nodes_from_paths(paths: List[List[str]]) -> Set[str]:
    nodes = set()
    for path in paths:
        nodes.update(path)
    return nodes


def count_node_usage(stories: List[Dict]) -> Counter:
    """Count how many stories use each node (for thickness)."""
    counter: Counter = Counter()
    for story in stories:
        nodes = collect_nodes_from_paths(story["paths"])
        for n in nodes:
            counter[n] += 1
    return counter


def count_edge_usage(stories: List[Dict]) -> Counter:
    counter: Counter = Counter()
    for story in stories:
        edges = collect_edges_from_paths(story["paths"])
        for e in edges:
            counter[e] += 1
    return counter


def dag_stories(stories: List[Dict]) -> List[Dict]:
    """Return only stories that have DAG paths."""
    return [s for s in stories if "paths" in s and s["paths"]]


def filter_stories(
    stories: List[Dict], data_filter: Optional[str]
) -> List[Dict]:
    if data_filter is None or data_filter == "both":
        return stories
    filtered = []
    for s in stories:
        if s.get("data_use") in (data_filter, "both"):
            filtered.append(s)
    return filtered


def pattern_to_dot(pattern: str) -> str:
    mapping = {
        "solid": "solid",
        "dashed": "dashed",
        "dotted": "dotted",
        "bold": "bold",
    }
    return mapping.get(pattern, "solid")


def node_shape(layer_name: str) -> str:
    shapes = {
        "config": "box3d",
        "categories": "box3d",
        "matching_cfg": "component",
        "start_journal": "note",
        "csv_txn": "cylinder",
        "receipt_img": "folder",
        "receipt_lbl": "tab",
        "matching_out": "diamond",
        "journal_out": "box",
        "visualization": "octagon",
    }
    return shapes.get(layer_name, "box")


def penwidth_for_count(count: int, is_edge: bool = False) -> float:
    if count <= 1:
        return 1.5 if is_edge else 1.0
    elif count <= 3:
        return 2.5 if is_edge else 1.5
    elif count <= 6:
        return 3.5 if is_edge else 2.0
    else:
        return 5.0 if is_edge else 3.0


# =========================================================================
# PlantUML DOT generation
# =========================================================================


def generate_dot_full(
    data: Dict,
    node_index: Dict,
    stories: List[Dict],
    highlight_story_id: Optional[str] = None,
    only_story_id: Optional[str] = None,
    info_fontsize: int = 10,
    info_acceptance_criteria: bool = False,
) -> Tuple[str, Optional[str]]:
    """Generate a Graphviz DOT diagram wrapped in PlantUML @startdot."""
    node_usage = count_node_usage(stories)
    edge_usage = count_edge_usage(stories)

    # Determine which nodes/edges to show
    if only_story_id:
        target = [s for s in stories if s["id"] == only_story_id]
        if not target:
            raise ValueError(f"Story {only_story_id} not found")
        visible_nodes = collect_nodes_from_paths(target[0]["paths"])
        visible_edges = collect_edges_from_paths(target[0]["paths"])
    else:
        visible_nodes = set()
        visible_edges = set()
        for s in stories:
            visible_nodes.update(collect_nodes_from_paths(s["paths"]))
            visible_edges.update(collect_edges_from_paths(s["paths"]))

    # Build layer -> nodes mapping (only visible)
    layer_nodes: Dict[str, List[str]] = defaultdict(list)
    for nid in visible_nodes:
        if nid in node_index:
            layer_nodes[node_index[nid]["layer"]].append(nid)

    lines = []
    lines.append("@startdot")
    lines.append("digraph userstory_dag {")
    lines.append('  rankdir=TB;')
    lines.append('  fontname="DejaVu Sans";')
    lines.append('  node [fontname="DejaVu Sans", fontsize=10];')
    lines.append('  edge [fontname="DejaVu Sans", fontsize=8];')
    lines.append("  newrank=true;")
    lines.append('  compound=true;')
    lines.append("")

    # Build side-panel HTML (rendered separately and composited onto the DAG)
    # For full/highlighted views: full legend with all stories
    # For isolated views: small info box with just the story details
    pattern_symbols = {
        "solid": "&#9473;&#9473;&#9473;",       # ━━━
        "dashed": "&#9476; &#9476; &#9476;",     # ╴ ╴ ╴
        "dotted": "&#183;&#183;&#183;&#183;&#183;&#183;",  # ······
        "bold": "&#9552;&#9552;&#9552;",         # ═══
    }
    legend_html = None
    if only_story_id:
        # Info box for the isolated story with full As a / I want / So that
        target_story = [s for s in stories if s["id"] == only_story_id]
        if target_story:
            s = target_story[0]
            c = s["colour"]
            pat = s.get("pattern", "solid")
            sym = pattern_symbols.get(pat, "&#9473;&#9473;&#9473;")
            title = s.get("title", s.get("label", ""))
            as_a = s.get("as_a", "")
            i_want = s.get("i_want", "")
            so_that = s.get("so_that", "")

            def _esc(text: str) -> str:
                """Escape HTML-sensitive characters for Graphviz labels."""
                return (text
                        .replace("&", "&amp;")
                        .replace("<", "&lt;")
                        .replace(">", "&gt;")
                        .replace('"', "&quot;"))

            def _wrap(text: str, width: int = 35) -> str:
                """Word-wrap text with HTML line breaks."""
                words = _esc(text).split()
                result_lines: List[str] = []
                line = ""
                for w in words:
                    if line and len(line) + 1 + len(w) > width:
                        result_lines.append(line)
                        line = w
                    else:
                        line = f"{line} {w}" if line else w
                if line:
                    result_lines.append(line)
                return "<BR/>".join(result_lines)

            body_fs = info_fontsize
            detail_fs = max(body_fs - 2, 6)
            ac_rows = ""
            if info_acceptance_criteria:
                ac_list = s.get("acceptance_criteria", [])
                if ac_list:
                    ac_items = "".join(
                        f'<BR/>&#8226; {_wrap(ac)}'
                        for ac in ac_list
                    )
                    ac_rows = (
                        f'<TR><TD ALIGN="LEFT"><FONT POINT-SIZE="{detail_fs}">'
                        f'<B>Acceptance criteria:</B>{ac_items}'
                        f'</FONT></TD></TR>'
                    )
            legend_html = (
                '<<TABLE BORDER="1" CELLBORDER="0" CELLSPACING="2"'
                ' CELLPADDING="4" BGCOLOR="#FAFAFA">'
                f'<TR><TD ALIGN="CENTER"><FONT POINT-SIZE="{body_fs + 2}">'
                f'<B>{_esc(s["id"])}</B></FONT></TD></TR>'
                f'<TR><TD ALIGN="CENTER"><FONT POINT-SIZE="{body_fs}">'
                f'<I>{_wrap(title)}</I></FONT></TD></TR>'
                f'<TR><TD ALIGN="LEFT"><FONT POINT-SIZE="{detail_fs}">'
                f'<B>As a</B> {_wrap(as_a)}'
                f'<BR/><B>I want to</B> {_wrap(i_want)}'
                f'<BR/><B>so that</B> {_wrap(so_that)}'
                f'</FONT></TD></TR>'
                + ac_rows +
                f'<TR><TD ALIGN="CENTER"><FONT COLOR="{c}">'
                f'{sym}</FONT></TD></TR>'
                "</TABLE>>"
            )
    elif not only_story_id:
        # Full legend for highlighted / all-stories views
        legend_rows = []
        for s in stories:
            c = s["colour"]
            pat = s.get("pattern", "solid")
            sym = pattern_symbols.get(pat, "&#9473;&#9473;&#9473;")
            legend_rows.append(
                f'<TR><TD ALIGN="LEFT"><FONT COLOR="{c}">'
                f'{sym} {s["id"]}: {s["label"]}</FONT></TD></TR>'
            )
        legend_html = (
            '<<TABLE BORDER="1" CELLBORDER="0" CELLSPACING="2"'
            ' CELLPADDING="4" BGCOLOR="#FAFAFA">'
            '<TR><TD ALIGN="CENTER"><B>Legend</B></TD></TR>'
            + "".join(legend_rows)
            + "</TABLE>>"
        )

    # Build a map of layer name -> label from data for placeholder use
    all_layer_labels = {}
    for layer in data["layers"]:
        all_layer_labels[layer["name"]] = layer["label"]

    # Build ordered list of (layer_name, node_ids_or_None) for all layers.
    # For isolated views, layers without visible nodes get a placeholder.
    ordered_layers: List[Tuple[str, Optional[List[str]]]] = []
    for layer_name in LAYER_ORDER:
        if layer_name in layer_nodes:
            ordered_layers.append((layer_name, sorted(layer_nodes[layer_name])))
        elif only_story_id and layer_name in all_layer_labels:
            ordered_layers.append((layer_name, None))  # placeholder

    # Emit layer subgraphs and placeholder nodes
    chain_nodes: List[str] = []  # ordered anchor nodes for vertical chain
    for layer_name, nids in ordered_layers:
        if nids is None:
            # Placeholder for a skipped layer
            lbl = all_layer_labels[layer_name]
            placeholder_id = f"_skip_{layer_name}"
            lines.append(f'  {placeholder_id} [label="{lbl}",'
                          f" shape=plaintext, fontsize=9,"
                          f' fontcolor="#AAAAAA"];')
            chain_nodes.append(placeholder_id)
            lines.append("")
            continue

        layer_label = node_index[nids[0]]["layer_label"]
        fill = LAYER_COLOURS.get(layer_name, "#FFFFFF")

        lines.append(f"  subgraph cluster_{layer_name} {{")
        lines.append(f'    label="{layer_label}";')
        lines.append(f'    style=filled; fillcolor="{fill}";')
        lines.append("    rank=same;")

        for nid in nids:
            info = node_index[nid]
            shape = node_shape(layer_name)
            pw = penwidth_for_count(node_usage.get(nid, 1))
            label = info["label"].replace("\n", "\\n")
            tooltip = info["desc"].replace('"', '\\"')

            # Greyed-out if highlighting a different story
            if highlight_story_id and nid not in _get_story_nodes(
                stories, highlight_story_id
            ):
                colour = "#CCCCCC"
                fontcolour = "#999999"
            else:
                colour = "#333333"
                fontcolour = "#000000"

            lines.append(
                f'    {nid} [label="{label}", shape={shape},'
                f' penwidth={pw}, color="{colour}",'
                f' fontcolor="{fontcolour}",'
                f' tooltip="{tooltip}"];'
            )
        lines.append("  }")
        chain_nodes.append(nids[0])
        lines.append("")

    # For isolated views, chain all layers (real and placeholder) with
    # invisible edges to enforce correct vertical ordering.
    if only_story_id and len(chain_nodes) > 1:
        for i in range(len(chain_nodes) - 1):
            src, dst = chain_nodes[i], chain_nodes[i + 1]
            is_placeholder = src.startswith("_skip_") or dst.startswith("_skip_")
            if is_placeholder:
                lines.append(
                    f"  {src} -> {dst}"
                    f' [style=dotted, color="#CCCCCC", arrowhead=none];'
                )
            else:
                lines.append(
                    f"  {src} -> {dst} [style=invis];"
                )
        lines.append("")

    # Edges
    if highlight_story_id:
        # Draw all edges grey first
        for src, dst in sorted(visible_edges):
            if src in node_index and dst in node_index:
                lines.append(
                    f'  {src} -> {dst} [color="#DDDDDD",'
                    f" penwidth=1.0, style=solid];"
                )
        # Then draw highlighted story edges on top
        target = [s for s in stories if s["id"] == highlight_story_id]
        if target:
            s = target[0]
            story_edges = collect_edges_from_paths(s["paths"])
            for src, dst in sorted(story_edges):
                pw = penwidth_for_count(edge_usage.get((src, dst), 1), True)
                style = pattern_to_dot(s["pattern"])
                lines.append(
                    f'  {src} -> {dst} [color="{s["colour"]}",'
                    f' penwidth={pw}, style={style},'
                    f' label="{s["id"]}"];'
                )
    elif only_story_id:
        target = [s for s in stories if s["id"] == only_story_id]
        if target:
            s = target[0]
            story_edges = collect_edges_from_paths(s["paths"])
            for src, dst in sorted(story_edges):
                style = pattern_to_dot(s["pattern"])
                lines.append(
                    f'  {src} -> {dst} [color="{s["colour"]}",'
                    f' penwidth=2.5, style={style}];'
                )
    else:
        # All stories — colour-coded edges
        # First pass: draw base grey for shared edges
        for (src, dst), count in sorted(edge_usage.items()):
            if src in visible_nodes and dst in visible_nodes:
                if count > 1:
                    pw = penwidth_for_count(count, True)
                    lines.append(
                        f'  {src} -> {dst} [color="#CCCCCC",'
                        f" penwidth={pw}, style=solid];"
                    )
        # Second pass: per-story coloured edges
        for s in stories:
            story_edges = collect_edges_from_paths(s["paths"])
            style = pattern_to_dot(s["pattern"])
            for src, dst in sorted(story_edges):
                if src in visible_nodes and dst in visible_nodes:
                    lines.append(
                        f'  {src} -> {dst} [color="{s["colour"]}",'
                        f' penwidth=1.5, style={style},'
                        f' tooltip="{s["id"]}"];'
                    )


    lines.append("}")
    lines.append("@enddot")
    return "\n".join(lines), legend_html


def _get_story_nodes(stories: List[Dict], story_id: str) -> Set[str]:
    for s in stories:
        if s["id"] == story_id:
            return collect_nodes_from_paths(s["paths"])
    return set()


# =========================================================================
# CLI (ASCII box-drawing) variant
# =========================================================================


def generate_cli_view(
    data: Dict,
    node_index: Dict,
    stories: List[Dict],
    story_id: str,
) -> str:
    """Generate an ASCII box-drawing representation of a single story path."""
    target = [s for s in stories if s["id"] == story_id]
    if not target:
        return f"Story {story_id} not found."
    story = target[0]
    node_usage = count_node_usage(stories)

    lines = []
    lines.append(f"{'=' * 72}")
    lines.append(f"  {story['id']}: {story['label']}")
    lines.append(f"  colour: {story['colour']}  pattern: {story['pattern']}")
    lines.append(f"  data_use: {story['data_use']}")
    lines.append(f"{'=' * 72}")
    lines.append("")

    for path_idx, path in enumerate(story["paths"]):
        if len(story["paths"]) > 1:
            lines.append(f"  Path {path_idx + 1}/{len(story['paths'])}:")
            lines.append("")

        prev_layer = None
        for i, nid in enumerate(path):
            info = node_index.get(nid)
            if not info:
                continue
            layer = info["layer_label"]
            usage = node_usage.get(nid, 1)

            # Thickness indicator
            if usage >= 6:
                bar = "┃"
                corner_d = "┣"
            elif usage >= 3:
                bar = "│"
                corner_d = "├"
            else:
                bar = "│"
                corner_d = "├"

            # Layer header
            if layer != prev_layer:
                if prev_layer is not None:
                    lines.append(f"  {bar}")
                    lines.append(f"  ▼")
                lines.append(f"  ┌─ {layer} ──────────────────────────")
                prev_layer = layer

            # Node box
            label = info["label"].replace("\n", " / ")
            usage_str = f"(used by {usage} stories)" if usage > 1 else ""
            lines.append(f"  {corner_d}  [{nid}]")
            lines.append(f"  {bar}    {label}  {usage_str}")
            lines.append(f"  {bar}    {info['desc']}")

        lines.append(f"  └──────────────────────────────────────")
        lines.append("")

    return "\n".join(lines)


# =========================================================================
# Main
# =========================================================================


def write_puml(filename: str, content: str, subdir: str = "") -> Path:
    target = OUTPUT_DIR / subdir if subdir else OUTPUT_DIR
    target.mkdir(parents=True, exist_ok=True)
    path = target / filename
    path.write_text(content, encoding="utf-8")
    return path


def render_puml(puml_path: Path) -> Optional[Path]:
    """Run plantuml to render the .puml file to PNG. Returns PNG path."""
    try:
        subprocess.run(
            ["plantuml", "-tpng", str(puml_path)],
            check=True,
            capture_output=True,
            timeout=120,
        )
        png = puml_path.with_suffix(".png")
        if png.exists():
            print(f"  Rendered: {png}")
            return png
        else:
            print(f"  Warning: plantuml ran but {png} not found")
    except FileNotFoundError:
        print("  Warning: plantuml not found, skipping render")
    except subprocess.CalledProcessError as e:
        print(f"  Warning: plantuml failed: {e.stderr.decode()[:200]}")
    return None


def _generate_legend_puml(legend_html: str) -> str:
    """Generate a standalone PlantUML DOT file for the legend only."""
    return (
        "@startdot\n"
        "digraph legend {\n"
        '  rankdir=TB;\n'
        '  fontname="DejaVu Sans";\n'
        '  node [fontname="DejaVu Sans", fontsize=10];\n'
        f"  legend_table [label={legend_html},"
        f" shape=plaintext, margin=0];\n"
        "}\n"
        "@enddot"
    )


def _composite_legend(dag_png: Path, legend_png: Path, gap: int = 4) -> None:
    """Paste the legend flush-left against the DAG content."""
    try:
        from PIL import Image
        import numpy as np
    except ImportError:
        print("  Warning: Pillow/numpy not installed, skipping composite")
        return
    dag = Image.open(dag_png).convert("RGBA")
    leg = Image.open(legend_png).convert("RGBA")

    # Find the leftmost non-white column in the DAG image so we can
    # place the legend right next to the actual content, not next to
    # the whitespace border that PlantUML adds.
    arr = np.array(dag)
    # non-white = any channel < 250 (accounting for antialiasing)
    non_white = np.any(arr[:, :, :3] < 250, axis=2)
    col_has_content = np.any(non_white, axis=0)
    if np.any(col_has_content):
        dag_left_edge = int(np.argmax(col_has_content))
    else:
        dag_left_edge = 0

    # Place legend so its right edge is `gap` pixels left of content
    legend_x = dag_left_edge - leg.width - gap
    if legend_x >= 0:
        # Legend fits within existing DAG whitespace
        canvas = dag.copy()
        canvas.paste(leg, (legend_x, 0), leg)
    else:
        # Need extra space on the left — expand the canvas
        extra = -legend_x
        canvas = Image.new("RGBA", (dag.width + extra, max(dag.height, leg.height)),
                            (255, 255, 255, 255))
        canvas.paste(dag, (extra, 0), dag)
        canvas.paste(leg, (0, 0), leg)
    canvas.save(dag_png)


def render_with_legend(
    puml_path: Path, legend_html: Optional[str]
) -> None:
    """Render a .puml file and composite the legend onto the top-left."""
    dag_png = render_puml(puml_path)
    if dag_png is None or legend_html is None:
        return
    # Write and render the legend in the same directory as the target
    target_dir = puml_path.parent
    legend_puml_path = target_dir / "_legend_tmp.puml"
    legend_puml_path.write_text(
        _generate_legend_puml(legend_html), encoding="utf-8"
    )
    legend_png = render_puml(legend_puml_path)
    if legend_png is None:
        return
    _composite_legend(dag_png, legend_png)
    # Clean up temp files
    legend_puml_path.unlink(missing_ok=True)
    legend_png.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(
        description="Generate PlantUML DAG diagrams from user story data."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--all", action="store_true", help="All stories overlaid"
    )
    group.add_argument("--story", type=str, help="Single story ID (e.g. US-3.2)")
    group.add_argument(
        "--each",
        action="store_true",
        help="Generate one file per story",
    )
    group.add_argument(
        "--list", action="store_true", help="List all story IDs"
    )
    parser.add_argument(
        "--context",
        choices=["isolated", "full"],
        default="isolated",
        help="For --story: isolated sub-graph or highlighted on full graph",
    )
    parser.add_argument(
        "--filter",
        choices=["test", "demo", "both"],
        default=None,
        help="Filter by data usage: test, demo, or both",
    )
    parser.add_argument(
        "--cli",
        action="store_true",
        help="Output ASCII box-drawing instead of PlantUML",
    )
    parser.add_argument(
        "--render",
        action="store_true",
        help="Also run plantuml to produce PNG files",
    )
    parser.add_argument(
        "--demo-paths",
        action="store_true",
        help="Use demo_paths instead of paths where available",
    )
    parser.add_argument(
        "--info-fontsize",
        type=int,
        default=10,
        help="Font point-size for the user story info box (default: 10)",
    )
    parser.add_argument(
        "--info-acceptance-criteria",
        action="store_true",
        default=False,
        help="Include acceptance criteria in the isolated story info box",
    )
    args = parser.parse_args()

    data = load_data()
    node_index = build_node_index(data)
    all_stories = data["stories"]

    # Only stories with DAG paths participate in diagram generation
    stories = dag_stories(all_stories)

    # Swap to demo_paths if requested
    if args.demo_paths:
        for s in stories:
            if "demo_paths" in s and s["demo_paths"]:
                s["paths"] = s["demo_paths"]

    stories = filter_stories(stories, args.filter)

    if args.list:
        for s in all_stories:
            label = s.get("label", s.get("title", ""))
            status = s.get("data_use", "-")
            has_dag = "*" if "paths" in s and s["paths"] else " "
            print(f"  {has_dag} {s['id']:12s}  {label:40s}  [{status}]")
        return

    if args.story:
        if args.cli:
            print(generate_cli_view(data, node_index, stories, args.story))
            return

        safe = args.story.replace(".", "_").replace("-", "_")
        if args.context == "full":
            dot, legend = generate_dot_full(
                data, node_index, stories, highlight_story_id=args.story,
                info_fontsize=args.info_fontsize,
                info_acceptance_criteria=args.info_acceptance_criteria,
            )
            path = write_puml(f"{safe}.puml", dot, subdir="highlighted")
        else:
            dot, legend = generate_dot_full(
                data, node_index, stories, only_story_id=args.story,
                info_fontsize=args.info_fontsize,
                info_acceptance_criteria=args.info_acceptance_criteria,
            )
            path = write_puml(f"{safe}.puml", dot, subdir="isolated")
        print(f"Written: {path}")
        if args.render:
            render_with_legend(path, legend)

    elif args.each:
        paths_written = []
        legend_for_path = {}
        for s in stories:
            safe = s["id"].replace(".", "_").replace("-", "_")

            # Isolated view -> isolated/ folder (story info box)
            dot, info_box = generate_dot_full(
                data, node_index, stories, only_story_id=s["id"],
                info_fontsize=args.info_fontsize,
                info_acceptance_criteria=args.info_acceptance_criteria,
            )
            p = write_puml(f"{safe}.puml", dot, subdir="isolated")
            paths_written.append(p)
            legend_for_path[p] = info_box

            # Full-context highlighted view -> highlighted/ folder
            dot_ctx, legend = generate_dot_full(
                data, node_index, stories, highlight_story_id=s["id"],
                info_fontsize=args.info_fontsize,
                info_acceptance_criteria=args.info_acceptance_criteria,
            )
            p_ctx = write_puml(f"{safe}.puml", dot_ctx, subdir="highlighted")
            paths_written.append(p_ctx)
            legend_for_path[p_ctx] = legend

        print(f"Written {len(paths_written)} files to {OUTPUT_DIR}/")
        if args.render:
            for p in paths_written:
                render_with_legend(p, legend_for_path[p])

    elif args.all:
        if args.cli:
            for s in stories:
                print(generate_cli_view(data, node_index, stories, s["id"]))
                print()
            return

        dot, legend = generate_dot_full(
            data, node_index, stories,
            info_fontsize=args.info_fontsize,
            info_acceptance_criteria=args.info_acceptance_criteria,
        )
        if args.filter and args.filter != "both":
            fname = f"dag_{args.filter}_only.puml"
        else:
            fname = "dag_all_stories.puml"
        path = write_puml(fname, dot)
        print(f"Written: {path}")
        if args.render:
            render_with_legend(path, legend)


if __name__ == "__main__":
    main()
