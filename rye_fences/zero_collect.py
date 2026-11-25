# -*- coding: utf-8 -*-
"""形その一: **柵の形をしていて、一度も走らない。**

★ この柵が生まれた実測（元のリポジトリ・2026-09-08）

  test_recall_pipeline.py は test_ で始まる名を持ちながら、中身は
  async def run_recall_test() ただ一つ。pytest は module を import して **0 件収集**して帰る。
  pytest --collect-only -q のファイル数（294）とディスク上の test_*.py（295）の差が 1 だった。
  ⚠ 誰もが「その柵が在る」と思っていて、実際には一行も走っていなかった。

★ 逆向きも在る。assert を持つのに名前が pytest に拾われないファイル（tests/checks.py の類）。
  こちらは find_unmatched_fences が見る。測るだけの道具（assert を一つも持たない計器）は通す
  ——通るのが正しい。

★ 収集される名前の見立ては pytest の既定に合わせる:
  module 直下の test* 関数、Test* クラス、そして unittest.TestCase の
  サブクラス（Test 接頭辞が無くても test* メソッドを持てば収集される。
  元の柵は 2026-10-16 にこの見落としを塞いだ）。
"""
from __future__ import annotations

import ast
import os
from fnmatch import fnmatch
from pathlib import Path
from typing import Iterable

from ._walk import (
    DEFAULT_SKIP,
    DEFAULT_TEST_DIR_NAMES,
    DEFAULT_TEST_FILE_PATTERNS,
    is_test_path,
    parse_python,
    rel,
    scan_tree,
)

#: 名前が拾われなくても柵ではない物。
DEFAULT_EXEMPT_FILES: tuple[str, ...] = ("conftest.py", "__init__.py")

_CASE_BASES = ("TestCase", "IsolatedAsyncioTestCase")


def collected_names(tree: ast.Module) -> list[str]:
    """pytest の既定（python_functions=test* / python_classes=Test* ＋ unittest）が
    module 直下から拾う名前を返す。"""
    names = [
        n.name
        for n in tree.body
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name.startswith("test")
    ]
    unittest_aliases = {"unittest"}
    case_names: set[str] = set()
    for n in tree.body:
        if isinstance(n, ast.Import):
            unittest_aliases.update(a.asname or a.name for a in n.names if a.name == "unittest")
        elif isinstance(n, ast.ImportFrom) and n.module == "unittest":
            case_names.update(a.asname or a.name for a in n.names if a.name in _CASE_BASES)
    for n in tree.body:
        if not isinstance(n, ast.ClassDef):
            continue
        is_case = any(
            (isinstance(b, ast.Name) and b.id in case_names)
            or (
                isinstance(b, ast.Attribute)
                and b.attr in _CASE_BASES
                and isinstance(b.value, ast.Name)
                and b.value.id in unittest_aliases
            )
            for b in n.bases
        )
        if is_case:
            case_names.add(n.name)  # 孫クラスも TestCase
        has_test_methods = any(
            isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef)) and m.name.startswith("test")
            for m in n.body
        )
        if n.name.startswith("Test") or (is_case and has_test_methods):
            names.append(n.name)
    return names


def has_assert(tree: ast.Module) -> bool:
    """どこかに assert 文が在るか。柵の芯。"""
    return any(isinstance(x, ast.Assert) for x in ast.walk(tree))


def _is_backup(name: str, marker: str | None) -> bool:
    return bool(marker) and marker in name


def find_empty_test_files(
    root: "str | os.PathLike[str]",
    patterns: Iterable[str] = DEFAULT_TEST_FILE_PATTERNS,
    skip=DEFAULT_SKIP,
    backup_marker: str | None = ".bak_",
) -> list[Path]:
    """test_*.py の名を持つのに、pytest が拾う関数もクラスも一つも無いファイル。

    import されるだけで一度も走らない。測るだけの道具なら test_ を外す。柵にするなら
    def test_… を書く。畳むなら退避へ。
    """
    pats = tuple(patterns)
    out: list[Path] = []
    for p in scan_tree(root, skip):
        if not any(fnmatch(p.name, pat) for pat in pats):
            continue
        if _is_backup(p.name, backup_marker):
            continue  # 退避は stray_backups の持ち場
        tree = parse_python(p)
        if tree is None:
            continue  # 構文の壊れたファイルは収集で赤くなる＝この柵の相手ではない
        if not collected_names(tree):
            out.append(p)
    return out


def find_unmatched_fences(
    root: "str | os.PathLike[str]",
    patterns: Iterable[str] = DEFAULT_TEST_FILE_PATTERNS,
    test_dir_names: Iterable[str] = DEFAULT_TEST_DIR_NAMES,
    skip=DEFAULT_SKIP,
    exempt: Iterable[str] = DEFAULT_EXEMPT_FILES,
    backup_marker: str | None = ".bak_",
) -> list[Path]:
    """テストの置き場に在って、assert か test* を持つのに、名前が pytest に拾われないファイル。

    conftest.py / __init__.py / assert を持たない計器は対象外。
    """
    pats = tuple(patterns)
    exempt_set = set(exempt)
    dirs = tuple(test_dir_names)
    out: list[Path] = []
    for p in scan_tree(root, skip):
        r = rel(p, root)
        if not is_test_path(r, dirs, ()):
            continue  # ディレクトリで判定（名前の形は今から見る）
        if any(fnmatch(p.name, pat) for pat in pats):
            continue
        if p.name in exempt_set or _is_backup(p.name, backup_marker):
            continue
        tree = parse_python(p)
        if tree is None:
            continue
        if collected_names(tree) or has_assert(tree):
            out.append(p)
    return out
