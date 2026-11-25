# -*- coding: utf-8 -*-
"""★ わざと壊して検出力を確かめる。

緑であることは、検出器である証拠にならない。assert が「何をしても通る」形になっているのは、
読んでいるだけでは判らない。だから偽物を植えて、赤くなることを見る。

元のリポジトリ（2026-09-08）は五つ植えて五つ赤を見た。ここでも同じことをする:
きれいな木の写しに偽物を**一つずつ**植え、植えた検出器だけが赤くなり、他は緑のままであることを縛る。
数は焼かず、名前・パスの集合で縛る。
"""
from __future__ import annotations

from pathlib import Path

import pytest

from rye_fences import (
    find_all_orphans,
    find_empty_test_files,
    find_importable_backups,
    find_orphans,
    find_present_tense_claims,
    find_unmatched_fences,
    run_all,
)
from rye_fences._walk import rel


def _rels(paths, root) -> set[str]:
    return {rel(p, root) for p in paths}


def test_clean_tree_is_green_on_every_detector(clean_tree: Path):
    rep = run_all(clean_tree, wide=True)
    assert rep.count == 0, rep


def test_sample_tree_each_planted_fake_is_caught_and_nothing_else(sample_tree: Path):
    """植えた物だけが見つかる。多くも少なくもなく。"""
    assert set(find_orphans(sample_tree)) == {"on_start_pipeline"}
    assert set(find_all_orphans(sample_tree)) == {"on_start_pipeline", "helper_unused"}
    assert _rels(find_empty_test_files(sample_tree), sample_tree) == {"tests/test_nothing.py"}
    assert _rels(find_importable_backups(sample_tree), sample_tree) == {"pkg/thing.bak_20250101.py"}
    claims = find_present_tense_claims(sample_tree)
    assert {(rel(c.path, sample_tree), c.line_no) for c in claims} == {("docs/report.md", 9), ("docs/report.md", 10)}
    assert find_unmatched_fences(sample_tree) == []  # こちらは tmp に植える（下）


def test_orphan_location_is_relpath_and_line(sample_tree: Path):
    assert find_orphans(sample_tree)["on_start_pipeline"] == "pkg/app.py:9"


#: (植える物, 赤くなるべき Report の欄)
FAKES = [
    pytest.param(
        {"pkg/late.py": "def on_start_later():\n    return 1\n"},
        "orphans",
        id="orphan-receiver",
    ),
    pytest.param(
        {"tests/test_measure.py": "async def run_measure():\n    return 1\n"},
        "empty_test_files",
        id="empty-test-file",
    ),
    pytest.param(
        {"tests/checks.py": "def check_it():\n    assert 1 == 1\n"},
        "unmatched_fences",
        id="unmatched-fence",
    ),
    pytest.param(
        {"pkg/app.bak_20250101.py": "VALUE = 1\n"},
        "importable_backups",
        id="importable-backup",
    ),
    pytest.param(
        {"docs/status.md": "## 環境の事実\n- 本体は走行中（14:03 起動）。\n"},
        "present_tense_claims",
        id="present-tense-claim",
    ),
]

FIELDS = ("orphans", "empty_test_files", "unmatched_fences", "importable_backups", "present_tense_claims")


@pytest.mark.parametrize("files,red_field", FAKES)
def test_one_fake_in_a_clean_copy_turns_exactly_one_detector_red(clean_copy: Path, files, red_field):
    for rel_path, body in files.items():
        p = clean_copy / rel_path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body, encoding="utf-8")
    rep = run_all(clean_copy)
    red = {f for f in FIELDS if getattr(rep, f)}
    assert red == {red_field}, f"expected only {red_field} to be red, got {red}"


def test_removing_the_fake_turns_it_green_again(clean_copy: Path):
    """赤→緑の往復。柵が一方向にしか動かない形（常に赤・常に緑）になっていないこと。"""
    fake = clean_copy / "pkg" / "late.py"
    fake.write_text("def on_start_later():\n    return 1\n", encoding="utf-8")
    assert set(find_orphans(clean_copy)) == {"on_start_later"}
    fake.unlink()
    assert find_orphans(clean_copy) == {}
