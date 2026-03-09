#!/usr/bin/env python3
"""Stitch existing segment MP4s into a full-path composite video.

Given a list of (mp4, markers_json) pairs, concatenates the videos with
ffmpeg and merges the marker timestamps (with time offsets) into a single
sidecar JSON.

Usage::

    python -m gifs.automation.stitch_full_path \\
        --segments \\
            gifs/1a_setup_config/output/cfg_1b.mp4 \\
            gifs/1b_add_category/output/cat_basic.mp4 \\
            gifs/2b_label_receipt/output/2b_label_receipt_dracula.mp4 \\
        --output gifs/2b_label_receipt/output/2b1_full_path.mp4
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple


def get_duration(mp4: Path) -> float:
    """Get the duration of an MP4 file in seconds."""
    result = subprocess.run(
        [
            "ffmpeg",
            "-i",
            str(mp4),
        ],
        capture_output=True,
        text=True,
    )
    # ffmpeg prints info to stderr
    for line in result.stderr.splitlines():
        if "Duration:" in line:
            # "  Duration: 00:01:04.08, ..."
            parts = line.split("Duration:")[1].split(",")[0].strip()
            h, m, s = parts.split(":")
            return int(h) * 3600 + int(m) * 60 + float(s)
    raise RuntimeError(f"Could not determine duration of {mp4}")


def load_markers(markers_json: Optional[Path]) -> Dict[str, float]:
    """Load markers from a sidecar JSON file."""
    if markers_json is None or not markers_json.exists():
        return {}
    with open(markers_json) as f:
        data = json.load(f)
    return data.get("markers", {})


def find_markers_json(mp4: Path) -> Optional[Path]:
    """Find the sidecar markers JSON for an MP4 file."""
    markers_path = mp4.with_name(mp4.stem + "_markers.json")
    if markers_path.exists():
        return markers_path
    return None


def stitch(
    segments: List[Path],
    output: Path,
) -> Dict[str, float]:
    """Concatenate MP4 segments and merge markers.

    Returns the merged marker dict with adjusted timestamps.
    """
    # Gather durations and markers
    durations: List[float] = []
    all_markers: List[Tuple[float, Dict[str, float]]] = []

    offset = 0.0
    for mp4 in segments:
        dur = get_duration(mp4)
        markers_json = find_markers_json(mp4)
        markers = load_markers(markers_json)
        all_markers.append((offset, markers))
        durations.append(dur)
        offset += dur

    # Merge markers with offsets
    merged: Dict[str, float] = {}
    for seg_offset, markers in all_markers:
        for node_id, ts in markers.items():
            adjusted = round(seg_offset + ts, 2)
            if node_id not in merged:
                merged[node_id] = adjusted

    # Concatenate with ffmpeg using the concat filter
    # Scale all inputs to the same resolution (use the largest)
    max_w = 0
    max_h = 0
    for mp4 in segments:
        result = subprocess.run(
            ["ffmpeg", "-i", str(mp4)],
            capture_output=True,
            text=True,
        )
        for line in result.stderr.splitlines():
            if "Stream" in line and "Video" in line:
                # parse "1464x1224" from the stream line
                import re

                m = re.search(r"(\d{3,5})x(\d{3,5})", line)
                if m:
                    w, h = int(m.group(1)), int(m.group(2))
                    max_w = max(max_w, w)
                    max_h = max(max_h, h)

    # Ensure even dimensions
    max_w = max_w + (max_w % 2)
    max_h = max_h + (max_h % 2)

    # Build ffmpeg filter_complex
    n = len(segments)
    inputs = []
    for mp4 in segments:
        inputs.extend(["-i", str(mp4)])

    # Normalise fps, scale + pad each input to max_w x max_h, then concat.
    # All streams must share the same frame rate for the concat filter;
    # without this, mismatched rates (e.g. 25 vs 50 fps) cause ffmpeg to
    # generate an astronomical number of frames and a corrupt output file.
    TARGET_FPS = 25
    filter_parts = []
    for i in range(n):
        filter_parts.append(
            f"[{i}:v]fps={TARGET_FPS},"
            f"scale={max_w}:{max_h}:force_original_aspect_ratio=decrease,"
            f"pad={max_w}:{max_h}:(ow-iw)/2:(oh-ih)/2:color=black,"
            f"setsar=1[v{i}]"
        )
    stream_labels = "".join(f"[v{i}]" for i in range(n))
    filter_parts.append(f"{stream_labels}concat=n={n}:v=1:a=0[outv]")
    filter_complex = ";".join(filter_parts)

    cmd = [
        "ffmpeg",
        "-y",
        *inputs,
        "-filter_complex",
        filter_complex,
        "-map",
        "[outv]",
        "-c:v",
        "libx264",
        "-crf",
        "23",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "faststart",
        str(output),
    ]

    print(f"Stitching {n} segments → {output}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"ffmpeg error:\n{result.stderr}", file=sys.stderr)
        sys.exit(1)

    total_dur = sum(durations)
    print(f"  Total duration: {total_dur:.1f}s ({max_w}x{max_h})")

    # Write merged markers JSON
    markers_out = output.with_name(output.stem + "_markers.json")
    markers_data = {
        "markers": merged,
        "total_duration": round(total_dur, 2),
        "segments": [
            {"file": seg.name, "duration": round(dur, 2)}
            for seg, dur in zip(segments, durations)
        ],
    }
    markers_out.write_text(json.dumps(markers_data, indent=2) + "\n")
    print(f"  Markers: {len(merged)} → {markers_out}")

    return merged


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Stitch segment MP4s into a full-path composite video."
    )
    parser.add_argument(
        "--segments",
        nargs="+",
        required=True,
        help="Ordered list of MP4 segment files to concatenate.",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Output MP4 path.",
    )
    args = parser.parse_args()

    segments = [Path(s) for s in args.segments]
    for s in segments:
        if not s.exists():
            print(f"Error: segment not found: {s}", file=sys.stderr)
            sys.exit(1)

    stitch(segments=segments, output=Path(args.output))


if __name__ == "__main__":
    main()
