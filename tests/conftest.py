# -*- coding: utf-8 -*-
"""柵の共通部品。木を一時ディレクトリへ書く小さな手。"""
from __future__ import annotations

import shutil
import textwrap
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = REPO_ROOT / "examples"


@pytest.fixture
def sample_tree() -> Path:
    """偽物を五つ植えた木（examples/sample_tree）。"""
    return EXAMPLES / "sample_tree"


@pytest.fixture
def clean_tree() -> Path:
    """きれいな木（examples/clean_tree）。"""
    return EXAMPLES / "clean_tree"


@pytest.fixture
def write_tree(tmp_path: Path):
    """{相対パス: 本文} を tmp_path へ書いて、その根を返す。本文は dedent する。"""

    def _write(files: dict[str, str]) -> Path:
        for rel, body in files.items():
            p = tmp_path / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(textwrap.dedent(body).lstrip("\n"), encoding="utf-8")
        return tmp_path

    return _write


@pytest.fixture
def clean_copy(tmp_path: Path, clean_tree: Path) -> Path:
    """きれいな木の写し。ここへ偽物を一つずつ植える。"""
    dst = tmp_path / "clean_copy"
    shutil.copytree(clean_tree, dst, ignore=shutil.ignore_patterns("__pycache__"))
    return dst
