# -*- coding: utf-8 -*-
"""自分のリポジトリの pytest に**一行で置ける**柵。

    from rye_fences.pytest_helpers import assert_no_orphans

    def test_every_receiver_has_a_caller():
        assert_no_orphans("src")

赤になったら、まず自分を疑う。柵を動かすのは最後。
assert 文ではなく AssertionError を明示的に投げるので、python -O でも消えない。
"""
from __future__ import annotations

import os
from typing import Iterable, Mapping

from ._walk import DEFAULT_SKIP, DEFAULT_TEST_DIR_NAMES, rel
from .cli import Report, format_report, run_all
from .orphans import (
    DEFAULT_WIRING_PATTERNS,
    MIN_REASON_LEN,
    check_allow_reasons,
    find_all_orphans,
    find_orphans,
)
from .present_tense import DEFAULT_SECTION_RE, find_present_tense_claims
from .stray_backups import find_importable_backups
from .zero_collect import find_empty_test_files, find_unmatched_fences


def _fail(head: str, items: Iterable[str], tail: str) -> None:
    body = "\n  ".join(items)
    raise AssertionError(f"{head}\n  {body}\n{tail}")


def assert_allow_has_reasons(allow: Mapping[str, str] | None, min_len: int = MIN_REASON_LEN) -> None:
    """allow の全部に理由が書かれていること。空文字の理由で通すのは柵を外すのと同じ。"""
    bad = check_allow_reasons(allow, min_len)
    if bad:
        _fail(
            f"allow entries without a reason of at least {min_len} characters:",
            bad,
            "An allow without a reason is the same as removing the fence. Write why no caller is fine.",
        )


def assert_no_orphans(
    root: "str | os.PathLike[str]",
    allow: Mapping[str, str] | None = None,
    patterns=DEFAULT_WIRING_PATTERNS,
    *,
    wide: bool = False,
    skip=DEFAULT_SKIP,
    test_dir_names: Iterable[str] = DEFAULT_TEST_DIR_NAMES,
) -> None:
    """配線の形をした関数は必ず呼ばれていること（wide=True で広い網も）。"""
    assert_allow_has_reasons(allow)
    dirs = tuple(test_dir_names)
    found = find_orphans(root, patterns=patterns, allow=allow, skip=skip, test_dir_names=dirs)
    if wide:
        found = {**found, **find_all_orphans(root, allow=allow, skip=skip, test_dir_names=dirs)}
    if found:
        _fail(
            "Receivers exist but nothing in the tree calls them:",
            (f"{n}  ({loc})" for n, loc in sorted(found.items())),
            "Wire a caller, fold the receiver away, or add it to allow with a written reason. "
            "A receiver placed to be wired later is exactly this shape.",
        )


def assert_no_empty_test_files(root: "str | os.PathLike[str]", *, skip=DEFAULT_SKIP, **kw) -> None:
    """test_*.py を名乗るファイルは必ず何かを収集させること。"""
    found = find_empty_test_files(root, skip=skip, **kw)
    if found:
        _fail(
            "Files named like tests that pytest would import and collect nothing from:",
            (rel(p, root) for p in found),
            "They never run. Drop the test_ prefix from measuring tools, or write a def test_.",
        )


def assert_no_unmatched_fences(root: "str | os.PathLike[str]", *, skip=DEFAULT_SKIP, **kw) -> None:
    """assert を持つファイルは pytest に拾われる名前であること。"""
    found = find_unmatched_fences(root, skip=skip, **kw)
    if found:
        _fail(
            "Files in a test location that hold asserts or test functions but are never collected:",
            (rel(p, root) for p in found),
            "Give them a test_ prefix, or take the asserts out if they are measuring tools.",
        )


def assert_no_importable_backups(
    root: "str | os.PathLike[str]", marker: str = ".bak_", *, skip=DEFAULT_SKIP
) -> None:
    """退避は拡張子まで潰してあること。"""
    found = find_importable_backups(root, marker=marker, skip=skip)
    if found:
        _fail(
            "Backups still end in .py and can be imported or collected:",
            (rel(p, root) for p in found),
            f"Rename to <name>.py{marker}<reason>_<timestamp> (extension last) or move them out of the tree.",
        )


def assert_no_present_tense_claims(
    root: "str | os.PathLike[str]", *, section_re: str = DEFAULT_SECTION_RE, skip=DEFAULT_SKIP, **kw
) -> None:
    """報告書の「環境の事実」が現在形で生存を主張していないこと。"""
    found = find_present_tense_claims(root, section_re=section_re, skip=skip, **kw)
    if found:
        _fail(
            "Report sections state liveness in the present tense (a reader will take it as today's fact):",
            (f"{rel(c.path, root)}:{c.line_no}  {c.text}" for c in found),
            "Close the sentence in the past tense and put the observation time first: "
            "HH:MM observed - ... was running.",
        )


def assert_all_fences(
    root: "str | os.PathLike[str]", allow: Mapping[str, str] | None = None, **kw
) -> Report:
    """四つ全部を一度に。通れば Report を返す（件数を報告に書くために）。"""
    rep = run_all(root, allow=allow, **kw)
    if rep.is_red:
        raise AssertionError(format_report(rep))
    return rep
