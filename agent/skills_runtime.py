"""Runtime skill workspace loader with drift checks."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SkillLoadResult:
    """Summary of source->runtime skill sync."""

    loaded_count: int
    copied_count: int
    source_dir: Path
    runtime_dir: Path


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(8192)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _default_runtime_dir() -> Path:
    override = os.getenv("KUBECLAW_RUNTIME_SKILLS_DIR", "").strip()
    if override:
        return Path(override)
    return Path.home() / ".kubeclaw" / "skills"


def sync_skills(
    *,
    source_dir: Path | None = None,
    runtime_dir: Path | None = None,
) -> SkillLoadResult:
    """Copy canonical skills into runtime workspace with drift validation."""
    src = source_dir or Path(__file__).resolve().parents[1] / "skills"
    dst = runtime_dir or _default_runtime_dir()
    dst.mkdir(parents=True, exist_ok=True)

    metadata_path = dst / ".skills-index.json"
    prior: dict[str, dict[str, str | float]] = {}
    if metadata_path.exists():
        prior = json.loads(metadata_path.read_text(encoding="utf-8"))

    current: dict[str, dict[str, str | float]] = {}
    copied = 0
    loaded = 0

    for skill in sorted(src.glob("*.md")):
        loaded += 1
        rel_name = skill.name
        src_hash = _sha256(skill)
        src_mtime = skill.stat().st_mtime
        target = dst / rel_name
        needs_copy = not target.exists()

        old = prior.get(rel_name, {})
        if old.get("sha256") != src_hash or float(old.get("mtime", 0.0)) < src_mtime:
            needs_copy = True

        if needs_copy:
            shutil.copy2(skill, target)
            copied += 1

        dst_hash = _sha256(target)
        if dst_hash != src_hash:
            raise RuntimeError(f"skill checksum mismatch after copy: {rel_name}")

        current[rel_name] = {"sha256": src_hash, "mtime": src_mtime}

    metadata_path.write_text(json.dumps(current, indent=2, sort_keys=True), encoding="utf-8")
    return SkillLoadResult(
        loaded_count=loaded,
        copied_count=copied,
        source_dir=src,
        runtime_dir=dst,
    )
