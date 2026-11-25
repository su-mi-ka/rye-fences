# -*- coding: utf-8 -*-
"""自分の木に自分の柵を当てる。

examples/ は偽物を植えた木なので避ける。それ以外（rye_fences/ と tests/）は四つとも 0 件でなければならない。
赤くなったら、まず自分を疑う。
"""
from __future__ import annotations

from pathlib import Path

from rye_fences import DEFAULT_SKIP, assert_all_fences, skip_also

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_own_tree_passes_its_own_fences():
    rep = assert_all_fences(REPO_ROOT, wide=True, skip=skip_also(DEFAULT_SKIP, "examples"))
    assert rep.wide_orphans == {}
