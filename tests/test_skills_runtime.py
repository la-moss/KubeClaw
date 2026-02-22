"""Runtime skills workspace sync tests."""

from __future__ import annotations

import json
from pathlib import Path

from agent.skills_runtime import sync_skills


def test_sync_skills_copies_and_indexes_files(tmp_path: Path) -> None:
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    src.mkdir()
    (src / "01_test.md").write_text("# one\n", encoding="utf-8")
    (src / "02_test.md").write_text("# two\n", encoding="utf-8")

    first = sync_skills(source_dir=src, runtime_dir=dst)
    assert first.loaded_count == 2
    assert first.copied_count == 2
    assert (dst / "01_test.md").exists()
    assert (dst / ".skills-index.json").exists()

    second = sync_skills(source_dir=src, runtime_dir=dst)
    assert second.loaded_count == 2
    assert second.copied_count == 0

    index = json.loads((dst / ".skills-index.json").read_text(encoding="utf-8"))
    assert "01_test.md" in index
    assert "sha256" in index["01_test.md"]
