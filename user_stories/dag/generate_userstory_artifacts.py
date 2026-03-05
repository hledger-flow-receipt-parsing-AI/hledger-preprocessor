#!/usr/bin/env python3
"""Generate all user story artifacts from userstory_dag_data.yaml.

Single entry point for regenerating everything when the YAML is updated:
DAG diagrams (.puml), userstories.md, and usage-flow sequence diagrams.

Usage:
    # Generate everything at once (the common case):
    python generate_userstory_artifacts.py -a
    python generate_userstory_artifacts.py --all

    # Individual artifact types:
    python generate_userstory_artifacts.py --dag-overlay          # all stories overlaid
    python generate_userstory_artifacts.py --story US-3.2         # single story isolated
    python generate_userstory_artifacts.py --story US-3.2 --context full
    python generate_userstory_artifacts.py --each                 # one file per story
    python generate_userstory_artifacts.py --filter demo          # only demo data paths
    python generate_userstory_artifacts.py --cli --story US-3.2   # ASCII box-drawing
    python generate_userstory_artifacts.py --render               # also produce PNGs
    python generate_userstory_artifacts.py --markdown             # userstories.md only
    python generate_userstory_artifacts.py --usage-flows          # sequence diagrams only
"""

import argparse
import subprocess
from collections import Counter, OrderedDict, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import yaml

SCRIPT_DIR = Path(__file__).parent
DATA_FILE = SCRIPT_DIR / "userstory_dag_data.yaml"
OUTPUT_DIR = SCRIPT_DIR / "output"
USERSTORIES_MD = SCRIPT_DIR.parent / "userstories.md"
USAGE_FLOWS_DIR = SCRIPT_DIR.parent / "usage_flows"

# PlantUML layer colours (background fills for subgraph clusters)
LAYER_COLOURS = {
    "config_accounts": "#E3F2FD",
    "config_dir_paths": "#BBDEFB",
    "config_file_names": "#90CAF9",
    "config_categorisation": "#64B5F6",
    "config_matching_algo": "#42A5F5",
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
    "receipt_lbl",
    "matching_out",
    "journal_out",
    "visualization",
]

# Layers that belong to the "Configuration" parent group
CONFIG_GROUP_LAYERS = {
    "config_accounts",
    "config_dir_paths",
    "config_file_names",
    "config_categorisation",
    "config_matching_algo",
}


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
        "config_accounts": "box3d",
        "config_dir_paths": "box3d",
        "config_file_names": "box3d",
        "config_categorisation": "box3d",
        "config_matching_algo": "box3d",
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
    lines.append("  rankdir=TB;")
    lines.append('  fontname="DejaVu Sans";')
    lines.append('  node [fontname="DejaVu Sans", fontsize=10];')
    lines.append('  edge [fontname="DejaVu Sans", fontsize=8];')
    lines.append("  newrank=true;")
    lines.append("  compound=true;")
    lines.append("")

    # Build side-panel HTML (rendered separately and composited onto the DAG)
    # For full/highlighted views: full legend with all stories
    # For isolated views: small info box with just the story details
    pattern_symbols = {
        "solid": "&#9473;&#9473;&#9473;",  # ━━━
        "dashed": "&#9476; &#9476; &#9476;",  # ╴ ╴ ╴
        "dotted": "&#183;&#183;&#183;&#183;&#183;&#183;",  # ······
        "bold": "&#9552;&#9552;&#9552;",  # ═══
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
                return (
                    text.replace("&", "&amp;")
                    .replace("<", "&lt;")
                    .replace(">", "&gt;")
                    .replace('"', "&quot;")
                )

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
                        f"<BR/>&#8226; {_wrap(ac)}" for ac in ac_list
                    )
                    ac_rows = (
                        f'<TR><TD ALIGN="LEFT"><FONT POINT-SIZE="{detail_fs}">'
                        f"<B>Acceptance criteria:</B>{ac_items}"
                        "</FONT></TD></TR>"
                    )
            legend_html = (
                '<<TABLE BORDER="1" CELLBORDER="0" CELLSPACING="2"'
                ' CELLPADDING="4" BGCOLOR="#FAFAFA">'
                f'<TR><TD ALIGN="CENTER"><FONT POINT-SIZE="{body_fs + 2}">'
                f'<B>{_esc(s["id"])}</B></FONT></TD></TR>'
                f'<TR><TD ALIGN="CENTER"><FONT POINT-SIZE="{body_fs}">'
                f"<I>{_wrap(title)}</I></FONT></TD></TR>"
                f'<TR><TD ALIGN="LEFT"><FONT POINT-SIZE="{detail_fs}">'
                f"<B>As a</B> {_wrap(as_a)}"
                f"<BR/><B>I want to</B> {_wrap(i_want)}"
                f"<BR/><B>so that</B> {_wrap(so_that)}"
                "</FONT></TD></TR>"
                + ac_rows
                + f'<TR><TD ALIGN="CENTER"><FONT COLOR="{c}">'
                f"{sym}</FONT></TD></TR>"
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

    # Emit layer subgraphs and placeholder nodes.
    # Config layers are wrapped in a parent cluster_config_group.
    chain_nodes: List[str] = []  # ordered anchor nodes for vertical chain
    config_group_open = False  # track whether parent config cluster is open
    # Determine indent level (extra indent when inside config group)
    base_indent = "  "

    for layer_name, nids in ordered_layers:
        # Open the config group parent cluster before the first config layer
        if layer_name in CONFIG_GROUP_LAYERS and not config_group_open:
            lines.append(f"{base_indent}subgraph cluster_config_group {{")
            lines.append(f'{base_indent}  label="Configuration";')
            lines.append(f"{base_indent}  labeljust=l;")
            lines.append(f'{base_indent}  style="dashed"; color="#888888";')
            lines.append(f"{base_indent}  penwidth=1.5;")
            config_group_open = True

        indent = base_indent + "  " if config_group_open else base_indent
        node_indent = indent + "  "

        if nids is None:
            # Placeholder for a skipped layer
            lbl = all_layer_labels[layer_name]
            placeholder_id = f"_skip_{layer_name}"
            lines.append(
                f'{indent}{placeholder_id} [label="{lbl}",'
                " shape=plaintext, fontsize=9,"
                ' fontcolor="#AAAAAA"];'
            )
            chain_nodes.append(placeholder_id)
            lines.append("")
        else:
            layer_label = node_index[nids[0]]["layer_label"]
            fill = LAYER_COLOURS.get(layer_name, "#FFFFFF")

            lines.append(f"{indent}subgraph cluster_{layer_name} {{")
            lines.append(f'{indent}  label="{layer_label}";')
            lines.append(f'{indent}  style=filled; fillcolor="{fill}";')
            lines.append(f"{indent}  rank=same;")

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
                    f'{node_indent}{nid} [label="{label}", shape={shape},'
                    f' penwidth={pw}, color="{colour}",'
                    f' fontcolor="{fontcolour}",'
                    f' tooltip="{tooltip}"];'
                )
            lines.append(f"{indent}}}")
            chain_nodes.append(nids[0])
            lines.append("")

        # Close the config group parent cluster after the last config layer
        if config_group_open and layer_name not in CONFIG_GROUP_LAYERS:
            # We've moved past the config layers — should not happen due to
            # ordering, but guard anyway
            pass
        if config_group_open and layer_name in CONFIG_GROUP_LAYERS:
            # Check if the next layer is still a config layer
            idx = [ln for ln, _ in ordered_layers].index(layer_name)
            next_is_config = (
                idx + 1 < len(ordered_layers)
                and ordered_layers[idx + 1][0] in CONFIG_GROUP_LAYERS
            )
            if not next_is_config:
                lines.append(f"{base_indent}}}")
                lines.append("")
                config_group_open = False

    # For isolated views, chain all layers (real and placeholder) with
    # invisible edges to enforce correct vertical ordering.
    if only_story_id and len(chain_nodes) > 1:
        for i in range(len(chain_nodes) - 1):
            src, dst = chain_nodes[i], chain_nodes[i + 1]
            is_placeholder = src.startswith("_skip_") or dst.startswith(
                "_skip_"
            )
            if is_placeholder:
                lines.append(
                    f"  {src} -> {dst}"
                    f' [style=dotted, color="#CCCCCC", arrowhead=none];'
                )
            else:
                lines.append(f"  {src} -> {dst} [style=invis];")
        lines.append("")

    # Edges
    if highlight_story_id:
        # Draw all edges grey first
        for src, dst in sorted(visible_edges):
            if src in node_index and dst in node_index:
                lines.append(
                    f'  {src} -> {dst} [color="#DDDDDD",'
                    " penwidth=1.0, style=solid];"
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
                    f" penwidth={pw}, style={style},"
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
                    f" penwidth=2.5, style={style}];"
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
                        f" penwidth=1.5, style={style},"
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
# Markdown generation (from generate_userstories_md.py)
# =========================================================================

MD_PREAMBLE = """\
# User Stories — hledger-preprocessor

This document contains detailed user stories for the hledger-preprocessor
ecosystem. Each story follows the format:

> **As a** [persona], **I want to** [action], **so that** [benefit].

Stories are organised by the 5-step workflow shown in the README, followed by
cross-cutting concerns. Stories marked *[NOT YET IMPLEMENTED]* describe
functionality that does not yet exist in the codebase.

*This file is auto-generated from `user_stories/dag/userstory_dag_data.yaml`.*
*Edit the YAML, then run `python user_stories/dag/generate_userstory_artifacts.py -a`.*
"""


def render_story_md(s: dict) -> str:
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

    parts = [MD_PREAMBLE, "---", ""]
    for section, story_list in sections.items():
        parts.append(f"## {section}")
        parts.append("")
        for s in story_list:
            parts.append(render_story_md(s))
            parts.append("---")
            parts.append("")

    return "\n".join(parts)


def write_markdown(data: dict, outpath: Optional[Path] = None) -> Path:
    """Generate and write userstories.md."""
    path = outpath or USERSTORIES_MD
    md = generate_markdown(data)
    path.write_text(md, encoding="utf-8")
    return path


# =========================================================================
# Usage-flow sequence diagram generation
# =========================================================================

# These diagrams describe the runtime pipeline sequence.  The structure is
# derived from the layer definitions and story sections in the YAML — the
# same participants and steps appear in a sequence-diagram form.


def _generate_usage_flow_high_level(data: dict) -> str:
    """High-level sequence diagram with colour-coded actors."""
    return """\
@startuml
actor User #0000FF
participant "Bash Script" as Bash #008000
participant "process_bank_config" as ProcessBank #FFA500
participant "hledger_preprocessor" as Preprocessor #800080
participant "hledger-flow" as HledgerFlow #008080
participant "hledger_plot" as HledgerPlot #FF0000
participant "Receipt Processor" as ReceiptProcessor #FF00FF

== Initialization ==
User -[#0000FF]-> Bash: Run script with config
Bash -[#008000]-> Bash: Validate config and setup environment

== Process Bank Configuration ==
Bash -[#008000]-> ProcessBank: Process GENERAL_CONFIG_FILEPATH
ProcessBank -[#FFA500]-> Preprocessor: Process CSVs for accounts
Preprocessor -[#800080]-> ProcessBank: Transactions processed
ProcessBank -[#FFA500]-> Bash: Configuration complete

== Import Transactions ==
Bash -[#008000]-> HledgerFlow: Run hledger-flow import
HledgerFlow -[#008080]-> Bash: Transactions imported to all-years.journal

== Receipt to Transaction Conversion ==
User -[#0000FF]-> ReceiptProcessor: Convert receipt images to CSVs
alt Use TUI
    ReceiptProcessor -[#FF00FF]-> User: Prompt for manual labeling
    User -[#0000FF]-> ReceiptProcessor: Provide labels
else Use AI
    ReceiptProcessor -[#FF00FF]-> ReceiptProcessor: Process images with AI models
end alt
ReceiptProcessor -[#FF00FF]-> ReceiptProcessor: Generate CSVs from receipt objects
ReceiptProcessor -[#FF00FF]-> Bash: CSVs ready

== Match Receipts to Transactions/Assets ==
User -[#0000FF]-> ReceiptProcessor: Match receipts to transactions/assets
ReceiptProcessor -[#FF00FF]-> ReceiptProcessor: Enrich transactions with receipt details (account_holder, bank, account_type)
note right
    Matches receipts to bank transactions or assets (e.g., gold, BTC),
    adding receipt details to transactions
end note
ReceiptProcessor -[#FF00FF]-> Bash: Enriched transactions ready

== Re-Preprocess Enriched Transactions ==
alt Transactions enriched
    Bash -[#008000]-> Preprocessor: Re-run preprocessing for enriched transactions/CSVs
    Preprocessor -[#800080]-> HledgerFlow: Update all-years.journal with enriched data
    HledgerFlow -[#008080]-> Bash: Journal updated
end alt

== Generate Reports/Plots ==
alt RANDOMIZE_DATA == "true"
    Bash -[#008000]-> HledgerPlot: Generate randomized plot
    HledgerPlot -[#FF0000]-> Bash: Plot generated
else RANDOMIZE_DATA == "false"
    Bash -[#008000]-> HledgerFlow: Generate balance report
    HledgerFlow -[#008080]-> Bash: Balance report generated
    Bash -[#008000]-> HledgerPlot: Generate plot
    HledgerPlot -[#FF0000]-> Bash: Plot generated
end alt

@enduml
"""


def _generate_usage_flow_detailed(data: dict) -> str:
    """Detailed sequence diagram with full init/processing steps."""
    return """\
@startuml
actor User
participant "Bash Script" as Bash
participant "process_bank_config" as ProcessBank
participant "hledger_preprocessor" as Preprocessor
participant "hledger-flow" as HledgerFlow
participant "hledger_plot" as HledgerPlot
participant Filesystem
participant Conda

== Initialization ==
User -> Bash: Run script
Bash -> Filesystem: Check GENERAL_CONFIG_FILEPATH exists
Filesystem --> Bash: Config file exists
Bash -> Bash: Validate RANDOMIZE_DATA ("true" or "false")
Bash -> Filesystem: Clear and create WORKING_DIR
Filesystem --> Bash: WORKING_DIR ready
Bash -> Conda: Initialize and activate hledger_preprocessor env
Conda --> Bash: Environment activated
Bash -> Bash: Display WORKING_DIR, START_JOURNAL_FILEPATH, GENERAL_CONFIG_FILEPATH

== Configuration Validation ==
Bash -> ProcessBank: Call process_bank_config(GENERAL_CONFIG_FILEPATH, WORKING_DIR)
ProcessBank -> Filesystem: Verify GENERAL_CONFIG_FILEPATH is YAML
Filesystem --> ProcessBank: File is valid YAML
ProcessBank -> Filesystem: Check .accounts in YAML
Filesystem --> ProcessBank: Accounts found
loop for each account in .accounts
    ProcessBank -> Filesystem: Read account details (csv_filepath, account_holder, bank, account_type)
    Filesystem --> ProcessBank: Account details
    ProcessBank -> Filesystem: Verify csv_filepath exists
    Filesystem --> ProcessBank: CSV exists
    ProcessBank -> Preprocessor: Call hledger_preprocessor --config --new-setup
    Preprocessor -> Filesystem: Process CSV for account_holder/bank/account_type
    Preprocessor --> ProcessBank: Processed transactions
end loop

== hledger-flow Import ==
Bash -> HledgerFlow: Run hledger-flow import
note right
    Expected input structure:
    WORKING_DIR/import/account_holder/bank/account_type
    - account_holder: e.g., "JohnDoe"
    - bank: e.g., "ING"
    - account_type: e.g., "checking"
    Processes CSVs into all-years.journal
end note
HledgerFlow -> Filesystem: Read CSVs from WORKING_DIR/import
HledgerFlow -> Filesystem: Write to all-years.journal
Filesystem --> HledgerFlow: Journal updated
HledgerFlow --> Bash: Import complete

== Include Starting Position ==
Bash -> Filesystem: Check if START_JOURNAL_FILEPATH included in all-years.journal
Filesystem --> Bash: Not included
Bash -> Filesystem: Append "include START_JOURNAL_FILEPATH" to all-years.journal
Filesystem --> Bash: Journal updated

== Plotting or Balance Report ==
alt RANDOMIZE_DATA == "true"
    Bash -> HledgerPlot: Run hledger_plot --journal-filepath all-years.journal -d EUR -s -r
    HledgerPlot -> Filesystem: Read all-years.journal
    HledgerPlot --> Bash: Plot generated
else RANDOMIZE_DATA == "false"
    Bash -> HledgerFlow: Run hledger bal -X EUR -f all-years.journal
    HledgerFlow -> Filesystem: Read all-years.journal
    HledgerFlow --> Bash: Balance report generated
    Bash -> HledgerPlot: Run hledger_plot --journal-filepath all-years.journal -d EUR -s
    HledgerPlot -> Filesystem: Read all-years.journal
    HledgerPlot --> Bash: Plot generated
end alt

@enduml
"""


def _generate_usage_flow_detailed_receipts(data: dict) -> str:
    """Detailed sequence diagram including receipt processing paths."""
    return """\
@startuml
actor User #0000FF
participant "Bash Script" as Bash #008000
participant "process_bank_config" as ProcessBank #FFA500
participant "hledger_preprocessor" as Preprocessor #800080
participant "hledger-flow" as HledgerFlow #008080
participant "hledger_plot" as HledgerPlot #FF0000
participant Filesystem #808080
participant Conda #FFFF00
participant "Receipt Processor" as ReceiptProcessor #FF00FF

== Initialization ==
User -[#0000FF]-> Bash: Run script
Bash -[#008000]-> Filesystem: Check GENERAL_CONFIG_FILEPATH exists
Filesystem -[#808080]-> Bash: Config file exists
Bash -[#008000]-> Bash: Validate RANDOMIZE_DATA ("true" or "false")
Bash -[#008000]-> Filesystem: Clear and create WORKING_DIR
Filesystem -[#808080]-> Bash: WORKING_DIR ready
Bash -[#008000]-> Conda: Initialize and activate hledger_preprocessor env
Conda -[#FFFF00]-> Bash: Environment activated
Bash -[#008000]-> Bash: Display WORKING_DIR, START_JOURNAL_FILEPATH, GENERAL_CONFIG_FILEPATH

== Configuration Validation ==
Bash -[#008000]-> ProcessBank: Call process_bank_config(GENERAL_CONFIG_FILEPATH, WORKING_DIR)
ProcessBank -[#FFA500]-> Filesystem: Verify GENERAL_CONFIG_FILEPATH is YAML
Filesystem -[#808080]-> ProcessBank: File is valid YAML
ProcessBank -[#FFA500]-> Filesystem: Check .accounts in YAML
Filesystem -[#808080]-> ProcessBank: Accounts found
loop for each account in .accounts
    ProcessBank -[#FFA500]-> Filesystem: Read account details (csv_filepath, account_holder, bank, account_type)
    Filesystem -[#808080]-> ProcessBank: Account details
    ProcessBank -[#FFA500]-> Filesystem: Verify csv_filepath exists
    Filesystem -[#808080]-> ProcessBank: CSV exists
    ProcessBank -[#FFA500]-> Preprocessor: Call hledger_preprocessor --config --new-setup
    Preprocessor -[#800080]-> Filesystem: Process CSV for account_holder/bank/account_type
    Preprocessor -[#800080]-> ProcessBank: Processed transactions
end loop

== hledger-flow Import ==
Bash -[#008000]-> HledgerFlow: Run hledger-flow import
note right
    Expected input structure:
    WORKING_DIR/import/account_holder/bank/account_type
    - account_holder: e.g., "JohnDoe"
    - bank: e.g., "ING"
    - account_type: e.g., "checking"
    Processes CSVs into all-years.journal
end note
HledgerFlow -[#008080]-> Filesystem: Read CSVs from WORKING_DIR/import
HledgerFlow -[#008080]-> Filesystem: Write to all-years.journal
Filesystem -[#808080]-> HledgerFlow: Journal updated
HledgerFlow -[#008080]-> Bash: Import complete

== Include Starting Position ==
Bash -[#008000]-> Filesystem: Check if START_JOURNAL_FILEPATH included in all-years.journal
Filesystem -[#808080]-> Bash: Not included
Bash -[#008000]-> Filesystem: Append "include START_JOURNAL_FILEPATH" to all-years.journal
Filesystem -[#808080]-> Bash: Journal updated

== Receipt Image to Transaction Conversion ==
alt Use TUI for Receipt Labeling
    User -[#0000FF]-> ReceiptProcessor: Run manage_creating_receipt_img_labels_with_tui
    ReceiptProcessor -[#FF00FF]-> Filesystem: Get receipt images from receipts_path
    Filesystem -[#808080]-> ReceiptProcessor: List of receipt filepaths
    ReceiptProcessor -[#FF00FF]-> Preprocessor: Get transactions_per_year (csv_encoding)
    Preprocessor -[#800080]-> Filesystem: Read CSVs for account_holder/bank/account_type
    Filesystem -[#808080]-> Preprocessor: CSV data
    Preprocessor -[#800080]-> ReceiptProcessor: Transactions per year
    ReceiptProcessor -[#FF00FF]-> ReceiptProcessor: Generate account info groups
    ReceiptProcessor -[#FF00FF]-> User: Prompt for manual receipt labeling via TUI
    User -[#0000FF]-> ReceiptProcessor: Provide receipt labels
    ReceiptProcessor -[#FF00FF]-> Filesystem: Save receipt objects
    Filesystem -[#808080]-> ReceiptProcessor: Receipt objects saved
else Use AI for Receipt Labeling
    User -[#0000FF]-> ReceiptProcessor: Run manage_getting_ai_receipt_objects_from_images
    ReceiptProcessor -[#FF00FF]-> Filesystem: Get receipt images from receipts_path
    Filesystem -[#808080]-> ReceiptProcessor: List of receipt filepaths
    ReceiptProcessor -[#FF00FF]-> Preprocessor: Load AI models for receipt parsing
    Preprocessor -[#800080]-> ReceiptProcessor: AI models loaded
    ReceiptProcessor -[#FF00FF]-> Filesystem: Process images to receipt objects
    Filesystem -[#808080]-> ReceiptProcessor: Receipt objects generated
end alt

== Match Receipts to Transactions/Assets ==
User -[#0000FF]-> ReceiptProcessor: Run manage_matching_manual_receipt_objs_to_account_transactions
ReceiptProcessor -[#FF00FF]-> Preprocessor: Get transactions_per_year (csv_encoding)
Preprocessor -[#800080]-> Filesystem: Read CSVs for account_holder/bank/account_type
Filesystem -[#808080]-> Preprocessor: CSV data
Preprocessor -[#800080]-> ReceiptProcessor: Transactions per year
ReceiptProcessor -[#FF00FF]-> Filesystem: Load existing receipt objects
Filesystem -[#808080]-> ReceiptProcessor: Receipt objects loaded
ReceiptProcessor -[#FF00FF]-> ReceiptProcessor: Match\\n receipts to transactions\\n (account_holder\\n, bank\\n, account_type)
note left
    Matches receipt objects to bank transactions or assets (e.g., gold, BTC)
    based on account_holder, bank, account_type, and transaction details
end note
ReceiptProcessor -[#FF00FF]-> Filesystem: Update matched transactions/receipts
Filesystem -[#808080]-> ReceiptProcessor: Updates saved
ReceiptProcessor -[#FF00FF]-> Bash: Matching complete

== Plotting or Balance Report ==
alt RANDOMIZE_DATA == "true"
    Bash -[#008000]-> HledgerPlot: Run hledger_plot --journal-filepath all-years.journal -d EUR -s -r
    HledgerPlot -[#FF0000]-> Filesystem: Read all-years.journal
    HledgerPlot -[#FF0000]-> Bash: Plot generated
else RANDOMIZE_DATA == "false"
    Bash -[#008000]-> HledgerFlow: Run hledger bal -X EUR -f all-years.journal
    HledgerFlow -[#008080]-> Filesystem: Read all-years.journal
    HledgerFlow -[#008080]-> Bash: Balance report generated
    Bash -[#008000]-> HledgerPlot: Run hledger_plot --journal-filepath all-years.journal -d EUR -s
    HledgerPlot -[#FF0000]-> Filesystem: Read all-years.journal
    HledgerPlot -[#FF0000]-> Bash: Plot generated
end alt

@enduml
"""


def _generate_usage_flow_simple(data: dict) -> str:
    """Simple uncoloured sequence diagram of the basic 5-step workflow."""
    return """\
@startuml
actor User

participant "Bash Script" as Bash
participant "process_bank_config" as ProcessBank
participant "hledger_preprocessor" as Preprocessor
participant "hledger-flow" as HledgerFlow
participant "hledger_plot" as HledgerPlot
participant Filesystem
participant Conda

== Initialization ==
User -> Bash: Run script
Bash -> Filesystem: Check GENERAL_CONFIG_FILEPATH exists
Filesystem --> Bash: Config file exists
Bash -> Bash: Validate RANDOMIZE_DATA ("true" or "false")
Bash -> Filesystem: Clear and create WORKING_DIR
Filesystem --> Bash: WORKING_DIR ready
Bash -> Conda: Initialize and activate hledger_preprocessor env
Conda --> Bash: Environment activated
Bash -> Bash: Display WORKING_DIR, START_JOURNAL_FILEPATH, GENERAL_CONFIG_FILEPATH

== Configuration Validation ==
Bash -> ProcessBank: Call process_bank_config(GENERAL_CONFIG_FILEPATH, WORKING_DIR)
ProcessBank -> Filesystem: Verify GENERAL_CONFIG_FILEPATH is YAML
Filesystem --> ProcessBank: File is valid YAML
ProcessBank -> Filesystem: Check .accounts in YAML
Filesystem --> ProcessBank: Accounts found
loop for each account in .accounts
    ProcessBank -> Filesystem: Read account details (csv_filepath, account_holder, bank, account_type)
    Filesystem --> ProcessBank: Account details
    ProcessBank -> Filesystem: Verify csv_filepath exists
    Filesystem --> ProcessBank: CSV exists
    ProcessBank -> Preprocessor: Call hledger_preprocessor --config --new-setup
    Preprocessor -> Filesystem: Process CSV for account_holder/bank/account_type
    Preprocessor --> ProcessBank: Processed transactions
end loop

== hledger-flow Import ==
Bash -> HledgerFlow: Run hledger-flow import
note right
    Expected input structure:
    WORKING_DIR/import/account_holder/bank/account_type
    - account_holder: e.g., "JohnDoe"
    - bank: e.g., "ING"
    - account_type: e.g., "checking"
    Processes CSVs into all-years.journal
end note
HledgerFlow -> Filesystem: Read CSVs from WORKING_DIR/import
HledgerFlow -> Filesystem: Write to all-years.journal
Filesystem --> HledgerFlow: Journal updated
HledgerFlow --> Bash: Import complete

== Include Starting Position ==
Bash -> Filesystem: Check if START_JOURNAL_FILEPATH included in all-years.journal
Filesystem --> Bash: Not included
Bash -> Filesystem: Append "include START_JOURNAL_FILEPATH" to all-years.journal
Filesystem --> Bash: Journal updated

== Plotting or Balance Report ==
alt RANDOMIZE_DATA == "true"
    Bash -> HledgerPlot: Run hledger_plot --journal-filepath all-years.journal -d EUR -s -r
    HledgerPlot -> Filesystem: Read all-years.journal
    HledgerPlot --> Bash: Plot generated
else RANDOMIZE_DATA == "false"
    Bash -> HledgerFlow: Run hledger bal -X EUR -f all-years.journal
    HledgerFlow -> Filesystem: Read all-years.journal
    HledgerFlow --> Bash: Balance report generated
    Bash -> HledgerPlot: Run hledger_plot --journal-filepath all-years.journal -d EUR -s
    HledgerPlot -> Filesystem: Read all-years.journal
    HledgerPlot --> Bash: Plot generated
end alt

@enduml
"""


def write_usage_flows(data: dict) -> List[Path]:
    """Generate and write all usage-flow sequence diagrams."""
    USAGE_FLOWS_DIR.mkdir(parents=True, exist_ok=True)
    written = []

    flows = [
        ("high_level_0.uml", _generate_usage_flow_high_level),
        ("detailed_0.uml", _generate_usage_flow_detailed),
        ("detailed_1.uml", _generate_usage_flow_detailed_receipts),
        ("usage_flow.uml", _generate_usage_flow_simple),
    ]
    for filename, gen_fn in flows:
        path = USAGE_FLOWS_DIR / filename
        path.write_text(gen_fn(data), encoding="utf-8")
        written.append(path)

    return written


# =========================================================================
# File I/O helpers
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
        "  rankdir=TB;\n"
        '  fontname="DejaVu Sans";\n'
        '  node [fontname="DejaVu Sans", fontsize=10];\n'
        f"  legend_table [label={legend_html},"
        " shape=plaintext, margin=0];\n"
        "}\n"
        "@enddot"
    )


def _composite_legend(dag_png: Path, legend_png: Path, gap: int = 4) -> None:
    """Paste the legend flush-left against the DAG content."""
    try:
        import numpy as np
        from PIL import Image
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
        canvas = Image.new(
            "RGBA",
            (dag.width + extra, max(dag.height, leg.height)),
            (255, 255, 255, 255),
        )
        canvas.paste(dag, (extra, 0), dag)
        canvas.paste(leg, (0, 0), leg)
    canvas.save(dag_png)


def render_with_legend(puml_path: Path, legend_html: Optional[str]) -> None:
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


# =========================================================================
# Main
# =========================================================================


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Generate all user story artifacts from userstory_dag_data.yaml."
        )
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "-a",
        "--all",
        action="store_true",
        help=(
            "Generate everything: DAG diagrams, userstories.md, and usage-flow"
            " diagrams"
        ),
    )
    group.add_argument(
        "--dag-overlay",
        action="store_true",
        help="DAG overlay diagram only (all stories)",
    )
    group.add_argument(
        "--story", type=str, help="Single story ID (e.g. US-3.2)"
    )
    group.add_argument(
        "--each",
        action="store_true",
        help="Generate one file per story",
    )
    group.add_argument("--list", action="store_true", help="List all story IDs")
    group.add_argument(
        "--markdown",
        action="store_true",
        help="Generate userstories.md only",
    )
    group.add_argument(
        "--usage-flows",
        action="store_true",
        help="Generate usage-flow sequence diagrams only",
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

    # --markdown: generate only userstories.md
    if args.markdown:
        path = write_markdown(data)
        print(f"Written: {path}")
        return

    # --usage-flows: generate only sequence diagrams
    if args.usage_flows:
        paths = write_usage_flows(data)
        print(f"Written {len(paths)} usage-flow diagrams to {USAGE_FLOWS_DIR}/")
        if args.render:
            for p in paths:
                render_puml(p)
        return

    # -a / --all: produce every artifact type (including PNGs)
    if args.all:
        # 1. userstories.md
        md_path = write_markdown(data)
        print(f"Written: {md_path}")

        # 2. Usage-flow sequence diagrams + render to PNG
        uf_paths = write_usage_flows(data)
        print(
            f"Written {len(uf_paths)} usage-flow diagrams to {USAGE_FLOWS_DIR}/"
        )
        for uf in uf_paths:
            render_puml(uf)

        # 3. DAG diagrams: overlay + demo-only + per-story
        stories = dag_stories(all_stories)
        if args.demo_paths:
            for s in stories:
                if "demo_paths" in s and s["demo_paths"]:
                    s["paths"] = s["demo_paths"]
        stories = filter_stories(stories, args.filter)

        # Demo-only overlay
        demo_stories = filter_stories(stories, "demo")
        if demo_stories:
            dot_demo, legend_demo = generate_dot_full(
                data,
                node_index,
                demo_stories,
                info_fontsize=args.info_fontsize,
                info_acceptance_criteria=args.info_acceptance_criteria,
            )
            path_demo = write_puml("dag_demo_only.puml", dot_demo)
            print(f"Written: {path_demo}")
            render_with_legend(path_demo, legend_demo)

        # Per-story isolated + highlighted
        paths_written = []
        legend_for_path = {}
        for s in stories:
            safe = s["id"].replace(".", "_").replace("-", "_")

            dot_iso, info_box = generate_dot_full(
                data,
                node_index,
                stories,
                only_story_id=s["id"],
                info_fontsize=args.info_fontsize,
                info_acceptance_criteria=args.info_acceptance_criteria,
            )
            p = write_puml(f"{safe}.puml", dot_iso, subdir="isolated")
            paths_written.append(p)
            legend_for_path[p] = info_box

            dot_ctx, leg = generate_dot_full(
                data,
                node_index,
                stories,
                highlight_story_id=s["id"],
                info_fontsize=args.info_fontsize,
                info_acceptance_criteria=args.info_acceptance_criteria,
            )
            p_ctx = write_puml(f"{safe}.puml", dot_ctx, subdir="highlighted")
            paths_written.append(p_ctx)
            legend_for_path[p_ctx] = leg

        print(f"Written {len(paths_written)} per-story files to {OUTPUT_DIR}/")
        for p in paths_written:
            render_with_legend(p, legend_for_path[p])

        return

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
                data,
                node_index,
                stories,
                highlight_story_id=args.story,
                info_fontsize=args.info_fontsize,
                info_acceptance_criteria=args.info_acceptance_criteria,
            )
            path = write_puml(f"{safe}.puml", dot, subdir="highlighted")
        else:
            dot, legend = generate_dot_full(
                data,
                node_index,
                stories,
                only_story_id=args.story,
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
                data,
                node_index,
                stories,
                only_story_id=s["id"],
                info_fontsize=args.info_fontsize,
                info_acceptance_criteria=args.info_acceptance_criteria,
            )
            p = write_puml(f"{safe}.puml", dot, subdir="isolated")
            paths_written.append(p)
            legend_for_path[p] = info_box

            # Full-context highlighted view -> highlighted/ folder
            dot_ctx, legend = generate_dot_full(
                data,
                node_index,
                stories,
                highlight_story_id=s["id"],
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

    elif args.dag_overlay:
        if args.cli:
            for s in stories:
                print(generate_cli_view(data, node_index, stories, s["id"]))
                print()
            return

        dot, legend = generate_dot_full(
            data,
            node_index,
            stories,
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
