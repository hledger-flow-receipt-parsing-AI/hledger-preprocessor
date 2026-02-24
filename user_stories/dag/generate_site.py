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
import json
import re
import shutil
import subprocess
import tempfile
from collections import OrderedDict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
DATA_FILE = SCRIPT_DIR / "userstory_dag_data.yaml"
GIFS_ROOT = PROJECT_ROOT / "gifs"
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

# Header patterns to search for in .cast files, mapped to DAG layer names.
LAYER_HEADER_PATTERNS: Dict[str, List[str]] = {
    "config": ["Setting up demo environment", "Step 1:"],
    "categories": ["categories", "Step 2: Define"],
    "receipt_img": ["Input: Receipt Image", "Receipt Image"],
    "receipt_lbl": ["Input: Receipt Label", "Receipt Label"],
    "csv_txn": ["Input: Bank CSV", "Bank CSV"],
    "matching_cfg": ["Matching Parameters", "matching"],
    "matching_out": [
        "Running: hledger_preprocessor",
        "Running:",
        "Preprocessing Assets",
    ],
    "journal_out": ["Result:", "Pipeline Complete", "Diff:"],
    "visualization": ["Visualiz", "SVG", "sankey", "treemap"],
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


def build_node_index(*, data: Dict) -> Dict[str, Dict]:
    """Build {node_id: {layer, label, desc}} from layers."""
    idx: Dict[str, Dict] = {}
    for layer in data.get("layers", []):
        for node in layer.get("nodes", []):
            idx[node["id"]] = {
                "layer": layer["name"],
                "layer_label": layer["label"],
                "label": node["label"],
                "desc": node.get("desc", ""),
            }
    return idx


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


def parse_cast_timestamps(
    *, cast_path: Path, layer_patterns: Dict[str, List[str]]
) -> Dict[str, float]:
    """Parse a .cast file and extract {layer_name: timestamp_seconds}."""
    timestamps: Dict[str, float] = {}
    try:
        with open(cast_path) as f:
            f.readline()  # skip header
            for line in f:
                row = json.loads(line)
                ts, _evt, data = row[0], row[1], row[2]
                clean = re.sub(r"\x1b\[[0-9;]*m", "", data)
                for layer, patterns in layer_patterns.items():
                    if layer in timestamps:
                        continue
                    for pat in patterns:
                        if pat in clean:
                            timestamps[layer] = round(ts, 2)
                            break
    except (json.JSONDecodeError, OSError):
        pass
    return timestamps


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


def get_timestamps_for_section(
    *,
    section: str,
    cast_map: Dict[str, Path],
) -> Dict[str, float]:
    """Get timestamps for a story section from its cast file."""
    gif_dir = SECTION_TO_GIF_DIR.get(section)
    if gif_dir and gif_dir in cast_map:
        return parse_cast_timestamps(
            cast_path=cast_map[gif_dir],
            layer_patterns=LAYER_HEADER_PATTERNS,
        )
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


def add_data_attributes_to_svg(
    *, svg: str, node_index: Dict[str, Dict]
) -> str:
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

    # Also add data-layer to cluster groups
    for layer_name in [
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

    # Make SVG responsive
    svg = svg.replace('width="', 'class="dag-svg" width="', 1)

    return svg


# ---------------------------------------------------------------------------
# HTML / CSS / JS generation
# ---------------------------------------------------------------------------
def generate_css() -> str:
    """Generate the site stylesheet."""
    return """\
:root {
  --sidebar-width: 260px;
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
  border-right: 1px solid var(--border); padding: 1rem;
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
.sidebar li a:hover, .sidebar li a.active {
  color: var(--accent); background: var(--bg-card); text-decoration: none;
}

/* Main content */
.main {
  margin-left: var(--sidebar-width); flex: 1;
  padding: 2rem; max-width: 1100px;
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
.dag-svg {
  max-width: 100%; height: auto;
  background: #fff; border-radius: 8px;
  border: 1px solid var(--border); padding: 0.5rem;
}
.dag-fallback-img {
  max-width: 100%; height: auto;
  background: #fff; border-radius: 8px;
  border: 1px solid var(--border); padding: 0.5rem;
}

/* DAG node highlighting */
.dag-node { cursor: pointer; transition: opacity 0.2s; }
.dag-node.active polygon,
.dag-node.active ellipse,
.dag-node.active rect { stroke: #ff6600 !important; stroke-width: 3 !important; }
.dag-node.active text { font-weight: bold !important; }
.dag-cluster.active-cluster > polygon { stroke: #ff6600 !important; stroke-width: 2 !important; }

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
  display: flex; flex-wrap: wrap; gap: 0.3rem;
  align-items: center; margin-bottom: 1rem;
}
.dag-path .path-node {
  font-size: 0.75rem; padding: 0.2rem 0.5rem;
  background: var(--bg-card); border: 1px solid var(--border);
  border-radius: 4px; cursor: pointer; transition: all 0.15s;
}
.dag-path .path-node:hover { border-color: var(--accent); }
.dag-path .path-node.active {
  border-color: #ff6600; background: rgba(255, 102, 0, 0.15);
  font-weight: 600;
}
.dag-path .path-arrow { color: var(--text-muted); font-size: 0.7rem; }

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
.overview-img {
  width: 100%; border-radius: 8px;
  border: 1px solid var(--border); background: #fff;
}
.coming-soon {
  text-align: center; padding: 2rem;
  color: var(--text-muted); font-style: italic;
  background: var(--bg-card); border-radius: 8px;
  border: 1px dashed var(--border);
}
"""


def generate_js() -> str:
    """Generate the video-DAG synchronization JavaScript module."""
    return """\
(function() {
  'use strict';
  const video = document.getElementById('demo-video');
  const svgContainer = document.querySelector('.dag-section');
  if (!video || !svgContainer || typeof TIMESTAMPS === 'undefined') return;

  const layers = Object.keys(TIMESTAMPS)
    .filter(k => TIMESTAMPS[k] !== null)
    .sort((a, b) => TIMESTAMPS[a] - TIMESTAMPS[b]);
  if (layers.length === 0) return;

  let currentIdx = 0;
  const nodes = svgContainer.querySelectorAll('.dag-node');
  const clusters = svgContainer.querySelectorAll('.dag-cluster');
  const pathNodes = document.querySelectorAll('.path-node');
  const layerIndicator = document.getElementById('layer-indicator-name');

  function highlightLayer(layerName) {
    nodes.forEach(n => n.classList.remove('active'));
    clusters.forEach(c => c.classList.remove('active-cluster'));
    pathNodes.forEach(n => n.classList.remove('active'));

    // Highlight nodes in this layer that are on the story path
    if (typeof NODE_PATH !== 'undefined') {
      nodes.forEach(n => {
        const nid = n.getAttribute('data-node');
        const nLayer = n.getAttribute('data-layer');
        if (nLayer === layerName && NODE_PATH.includes(nid)) {
          n.classList.add('active');
        }
      });
    } else {
      svgContainer.querySelectorAll('[data-layer="' + layerName + '"]').forEach(n => {
        if (n.classList.contains('dag-node')) n.classList.add('active');
      });
    }

    // Highlight cluster
    clusters.forEach(c => {
      if (c.getAttribute('data-layer') === layerName) {
        c.classList.add('active-cluster');
      }
    });

    // Highlight path node chip
    pathNodes.forEach(n => {
      if (n.getAttribute('data-layer') === layerName) {
        n.classList.add('active');
      }
    });

    // Update indicator
    if (layerIndicator) {
      layerIndicator.textContent = layerName.replace(/_/g, ' ');
    }

    // Update currentIdx
    const idx = layers.indexOf(layerName);
    if (idx >= 0) currentIdx = idx;
  }

  // Sync: video time -> DAG highlight
  video.addEventListener('timeupdate', function() {
    const t = video.currentTime;
    let active = layers[0];
    for (const layer of layers) {
      if (TIMESTAMPS[layer] <= t) active = layer;
    }
    highlightLayer(active);
  });

  // Keyboard: Up/Down jump between layers
  document.addEventListener('keydown', function(e) {
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
    if (e.key === 'ArrowDown' || e.key === 'j') {
      e.preventDefault();
      currentIdx = Math.min(currentIdx + 1, layers.length - 1);
      video.currentTime = TIMESTAMPS[layers[currentIdx]];
      video.play();
    } else if (e.key === 'ArrowUp' || e.key === 'k') {
      e.preventDefault();
      currentIdx = Math.max(currentIdx - 1, 0);
      video.currentTime = TIMESTAMPS[layers[currentIdx]];
      video.play();
    } else if (e.key === ' ' && e.target === document.body) {
      e.preventDefault();
      if (video.paused) video.play();
      else video.pause();
    }
  });

  // Click DAG node -> jump video
  nodes.forEach(function(node) {
    node.addEventListener('click', function() {
      const layer = node.getAttribute('data-layer');
      if (layer && TIMESTAMPS[layer] !== undefined) {
        video.currentTime = TIMESTAMPS[layer];
        video.play();
      }
    });
  });

  // Click path node chip -> jump video
  pathNodes.forEach(function(chip) {
    chip.addEventListener('click', function() {
      const layer = chip.getAttribute('data-layer');
      if (layer && TIMESTAMPS[layer] !== undefined) {
        video.currentTime = TIMESTAMPS[layer];
        video.play();
      }
    });
  });

  // Initialize with first layer
  highlightLayer(layers[0]);
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


def _sidebar_html(
    *,
    sections: "OrderedDict[str, List[Dict]]",
    current_story_id: Optional[str] = None,
) -> str:
    html = '<nav class="sidebar">\n'
    html += '<h1><a href="{INDEX_PATH}">hledger-preprocessor</a></h1>\n'
    html += "<p style=\"font-size:0.75rem;color:var(--text-muted);margin-bottom:1rem\">"
    html += "User Story DAG Explorer</p>\n"
    for section, stories in sections.items():
        is_current = current_story_id and any(
            s["id"] == current_story_id for s in stories
        )
        open_attr = " open" if is_current else ""
        html += f"<details{open_attr}>\n"
        html += f"<summary>{_esc(section)}</summary>\n<ul>\n"
        for s in stories:
            active = ' class="active"' if s["id"] == current_story_id else ""
            html += (
                f'<li><a href="{{STORIES_PATH}}/{s["id"]}.html"{active}>'
                f'{s["id"]}: {_esc(s["title"])}</a></li>\n'
            )
        html += "</ul>\n</details>\n"
    html += "</nav>\n"
    return html


def generate_index_html(
    *,
    sections: "OrderedDict[str, List[Dict]]",
    has_overview_img: bool,
) -> str:
    head = _html_head(title="User Story DAG — hledger-preprocessor")
    head = head.replace("{CSS_PATH}", "assets/css/style.css")
    sidebar = _sidebar_html(sections=sections)
    sidebar = sidebar.replace("{INDEX_PATH}", "index.html")
    sidebar = sidebar.replace("{STORIES_PATH}", "stories")

    main = '<div class="main">\n'
    main += "<h1>User Story DAG</h1>\n"
    main += "<p style=\"margin-bottom:1.5rem;color:var(--text-muted)\">"
    main += "Interactive explorer for hledger-preprocessor user stories. "
    main += "Click a story in the sidebar to view its demo video synchronized "
    main += "with the DAG diagram.</p>\n"

    if has_overview_img:
        main += '<img class="overview-img" src="assets/images/dag_all_stories.png" '
        main += 'alt="Full DAG overview">\n'
    main += "</div>\n"

    return head + sidebar + main + "</body>\n</html>\n"


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
) -> str:
    sid = story["id"]
    head = _html_head(title=f"{sid}: {story['title']} — hledger-preprocessor")
    head = head.replace("{CSS_PATH}", "../assets/css/style.css")
    sidebar = _sidebar_html(sections=sections, current_story_id=sid)
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

    main = '<div class="main">\n'
    # Story header
    main += f'<div class="story-header" style="border-left-color:{colour}">\n'
    main += f'<span class="story-id">{_esc(sid)}{badge}</span>\n'
    main += f"<h1>{_esc(story['title'])}</h1>\n"
    main += "</div>\n"

    # Video section
    main += '<div class="video-section">\n'
    if video_filename:
        if is_gif:
            main += (
                f'<img src="../assets/videos/{video_filename}" '
                f'alt="Demo: {_esc(story["title"])}">\n'
            )
        else:
            main += (
                f'<video id="demo-video" controls loop preload="metadata">\n'
                f'<source src="../assets/videos/{video_filename}" '
                f'type="video/mp4">\n'
                f"</video>\n"
            )
        main += '<div class="video-hint">'
        main += "&#x2191;&#x2193; arrows or j/k to jump between DAG nodes "
        main += "&middot; click a node to seek &middot; space to play/pause"
        main += "</div>\n"
    else:
        main += '<div class="coming-soon">Demo video coming soon</div>\n'
    main += "</div>\n"

    # Layer indicator
    if timestamps:
        main += '<div class="layer-indicator">\n'
        main += '<span class="layer-dot"></span>\n'
        main += 'Current layer: <span class="layer-name" id="layer-indicator-name">—</span>\n'
        main += "</div>\n"

    # DAG path chips
    if node_path:
        main += '<div class="dag-path">\n'
        for i, nid in enumerate(node_path):
            info = node_index.get(nid, {})
            layer = info.get("layer", "")
            label = info.get("label", nid).split("\n")[0]
            has_ts = layer in timestamps
            cls = "path-node" + (" clickable" if has_ts else "")
            main += f'<span class="{cls}" data-layer="{layer}" data-node="{nid}"'
            main += f' title="{_esc(info.get("desc", ""))}">{_esc(label)}</span>\n'
            if i < len(node_path) - 1:
                main += '<span class="path-arrow">→</span>\n'
        main += "</div>\n"

    # SVG DAG diagram
    main += '<div class="dag-section">\n'
    main += "<h2>DAG Diagram</h2>\n"
    if svg_content:
        main += svg_content + "\n"
    elif has_png_fallback:
        safe = story_id_to_safe(story_id=sid)
        main += (
            f'<img class="dag-fallback-img" '
            f'src="../assets/images/isolated/{safe}.png" '
            f'alt="DAG for {_esc(sid)}">\n'
        )
    main += "</div>\n"

    # BDD narrative
    main += '<h2>User Story</h2>\n<dl class="bdd">\n'
    if story.get("as_a"):
        main += f"<dt>As a</dt><dd>{_esc(story['as_a'])}</dd>\n"
    if story.get("i_want"):
        main += f"<dt>I want to</dt><dd>{_esc(story['i_want'])}</dd>\n"
    if story.get("so_that"):
        main += f"<dt>So that</dt><dd>{_esc(story['so_that'])}</dd>\n"
    main += "</dl>\n"

    # Acceptance criteria
    criteria = story.get("acceptance_criteria", [])
    if criteria:
        main += '<h2>Acceptance Criteria</h2>\n<ul class="criteria">\n'
        for c in criteria:
            main += f"<li>{_esc(c)}</li>\n"
        main += "</ul>\n"

    # Prev / Next
    main += '<div class="nav-links">\n'
    if prev_story:
        main += (
            f'<a href="{prev_story["id"]}.html">'
            f'← {prev_story["id"]}</a>\n'
        )
    else:
        main += "<span></span>\n"
    if next_story:
        main += (
            f'<a href="{next_story["id"]}.html">'
            f'{next_story["id"]} →</a>\n'
        )
    else:
        main += "<span></span>\n"
    main += "</div>\n"
    main += "</div>\n"

    # Timestamp manifest + JS
    js_block = ""
    if video_filename and not is_gif:
        ts_json = json.dumps(timestamps)
        path_json = json.dumps(node_path)
        js_block = (
            f"<script>\nconst TIMESTAMPS = {ts_json};\n"
            f"const NODE_PATH = {path_json};\n</script>\n"
            f'<script src="../assets/js/dag-sync.js"></script>\n'
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
    sections: "OrderedDict[str, List[Dict]]",
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

    # Copy overview DAG
    overview = SCRIPT_DIR / "output" / "dag_all_stories.png"
    if overview.exists():
        shutil.copy2(overview, img_dir / "dag_all_stories.png")

    # Copy isolated PNGs
    iso_src = SCRIPT_DIR / "output" / "isolated"
    if iso_src.is_dir():
        for png in iso_src.glob("*.png"):
            shutil.copy2(png, iso_dir / png.name)

    # Copy videos (one per section)
    copied: set = set()
    for section in sections:
        vid = get_video_for_section(section=section, video_map=video_map)
        if vid and vid.name not in copied:
            shutil.copy2(vid, vid_dir / vid.name)
            copied.add(vid.name)

    # Write CSS and JS
    (css_dir / "style.css").write_text(generate_css())
    (js_dir / "dag-sync.js").write_text(generate_js())


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
    args = parser.parse_args()
    output_dir = args.output

    print(f"Loading data from {DATA_FILE}...")
    data = load_data()
    all_stories = data.get("stories", [])
    stories = dag_stories(stories=all_stories)
    node_index = build_node_index(data=data)
    sections = group_stories_by_section(stories=stories)

    print(f"Found {len(stories)} stories with DAG paths in {len(sections)} sections.")

    # Discover videos and cast files
    video_map = discover_videos(gifs_root=GIFS_ROOT, theme=DEFAULT_THEME)
    cast_map = discover_cast_files(gifs_root=GIFS_ROOT)
    print(f"Found {len(video_map)} video dirs, {len(cast_map)} cast files.")

    # Copy assets
    print(f"Copying assets to {output_dir}...")
    copy_assets(
        output_dir=output_dir,
        video_map=video_map,
        sections=sections,
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

    # Check overview image
    has_overview = (output_dir / "assets" / "images" / "dag_all_stories.png").exists()

    # Generate index.html
    print("Generating index.html...")
    index_html = generate_index_html(
        sections=sections,
        has_overview_img=has_overview,
    )
    (output_dir / "index.html").write_text(index_html)

    # Generate per-story pages
    print("Generating story pages...")
    flat = list(stories)
    for i, story in enumerate(flat):
        prev_s = flat[i - 1] if i > 0 else None
        next_s = flat[i + 1] if i < len(flat) - 1 else None
        section = story.get("section", "")

        # Video
        vid = get_video_for_section(section=section, video_map=video_map)
        video_filename = vid.name if vid else None
        is_gif = video_filename.endswith(".gif") if video_filename else False

        # Timestamps
        timestamps = get_timestamps_for_section(
            section=section, cast_map=cast_map
        )

        # Node path (first path)
        node_path = story.get("paths", [[]])[0] if story.get("paths") else []

        # SVG
        safe = story_id_to_safe(story_id=story["id"])
        svg_content = svg_cache.get(safe) if not args.no_svg else None
        has_png = (
            output_dir / "assets" / "images" / "isolated" / f"{safe}.png"
        ).exists()

        story_html = generate_story_html(
            story=story,
            sections=sections,
            prev_story=prev_s,
            next_story=next_s,
            video_filename=video_filename,
            is_gif=is_gif,
            svg_content=svg_content,
            has_png_fallback=has_png,
            timestamps=timestamps,
            node_path=node_path,
            node_index=node_index,
        )
        (output_dir / "stories" / f"{story['id']}.html").write_text(
            story_html
        )

    print(f"Done! Site generated at {output_dir}/")
    print(f"  {len(flat)} story pages + index.html")
    print(f"  Open {output_dir}/index.html in a browser to preview.")


if __name__ == "__main__":
    main()
