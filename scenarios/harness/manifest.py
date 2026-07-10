"""Load and represent a scenario manifest.

A manifest is a plain YAML file (``scenarios/<id>.yaml``) with these top-level
keys: ``id``, ``title``, ``section``, ``gif_video``, ``fixtures``, ``script``,
``expect``, ``dag``.  This module keeps the manifest as a thin typed wrapper so
the harness, the resolver, the DAG derivation and the tests all read exactly
the same declaration.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

import yaml

# scenarios/ directory (parent of harness/)
SCENARIOS_DIR = Path(__file__).resolve().parent.parent
# repo root = hledger-preprocessor/
REPO_ROOT = SCENARIOS_DIR.parent
RUNS_DIR = SCENARIOS_DIR / "_runs"


@dataclass
class Manifest:
    """Typed view over a scenario manifest YAML."""

    path: Path
    data: dict[str, Any]

    @property
    def id(self) -> str:
        return self.data["id"]

    @property
    def slug(self) -> str:
        """Filesystem-safe id, e.g. ``US-2b.1`` -> ``us_2b_1``."""
        return self.id.lower().replace("-", "_").replace(".", "_")

    @property
    def title(self) -> str:
        return self.data.get("title", self.id)

    @property
    def section(self) -> str:
        return self.data.get("section", "")

    @property
    def gif_video(self) -> str:
        return self.data.get("gif_video", "")

    @property
    def fixtures(self) -> dict[str, Any]:
        return self.data.get("fixtures", {})

    @property
    def script(self) -> dict[str, Any]:
        return self.data.get("script", {})

    @property
    def expect(self) -> dict[str, Any]:
        return self.data.get("expect", {})

    @property
    def dag(self) -> dict[str, Any]:
        return self.data.get("dag", {})

    @property
    def run_record_path(self) -> Path:
        return RUNS_DIR / f"{self.slug}.run.json"


def manifest_path_for(scenario: str) -> Path:
    """Resolve a scenario id/slug/path to a manifest file path."""
    p = Path(scenario)
    if p.suffix == ".yaml" and p.exists():
        return p
    slug = scenario.lower().replace("-", "_").replace(".", "_")
    candidate = SCENARIOS_DIR / f"{slug}.yaml"
    if candidate.exists():
        return candidate
    raise FileNotFoundError(
        f"No scenario manifest for {scenario!r} (looked for {candidate})"
    )


def load_manifest(scenario: str) -> Manifest:
    """Load a manifest by scenario id (``US-2b.1``), slug, or file path."""
    path = manifest_path_for(scenario)
    with open(path) as f:
        data = yaml.safe_load(f)
    return Manifest(path=path, data=data)


def all_manifests() -> list[Manifest]:
    """Load every scenario manifest under scenarios/ (skips overlays)."""
    out: list[Manifest] = []
    for f in sorted(SCENARIOS_DIR.glob("*.yaml")):
        try:
            with open(f) as fh:
                data = yaml.safe_load(fh)
        except Exception:  # nosec B112 - skip unreadable/non-manifest yaml
            continue
        if isinstance(data, dict) and "id" in data and "script" in data:
            out.append(Manifest(path=f, data=data))
    return out
