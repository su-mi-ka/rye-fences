# -*- coding: utf-8 -*-
"""python -m rye_fences <root> — 四つの検出器を一度に走らせ、件数と場所を出す。

終了コード: 0 = 何も無い（緑）／ 1 = 一件でも在る（赤）／ 2 = 引数の誤り。
"""
from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Mapping

from ._walk import DEFAULT_SKIP, DEFAULT_TEST_DIR_NAMES, rel
from .orphans import (
    DEFAULT_WIRING_PATTERNS,
    OPTIONAL_JA_PATTERNS,
    check_allow_reasons,
    find_all_orphans,
    find_orphans,
)
from .present_tense import DEFAULT_SECTION_RE, Claim, find_present_tense_claims
from .stray_backups import find_importable_backups
from .zero_collect import find_empty_test_files, find_unmatched_fences


@dataclass
class Report:
    """一度の走査の結果。数は焼かず、中身（名前・場所）を持つ。"""

    root: Path
    orphans: dict[str, str] = field(default_factory=dict)
    wide_orphans: dict[str, str] | None = None  # wide=False なら None
    empty_test_files: list[Path] = field(default_factory=list)
    unmatched_fences: list[Path] = field(default_factory=list)
    importable_backups: list[Path] = field(default_factory=list)
    present_tense_claims: list[Claim] = field(default_factory=list)
    bad_allow_reasons: list[str] = field(default_factory=list)

    @property
    def count(self) -> int:
        return (
            len(self.orphans)
            + len(self.wide_orphans or {})
            + len(self.empty_test_files)
            + len(self.unmatched_fences)
            + len(self.importable_backups)
            + len(self.present_tense_claims)
            + len(self.bad_allow_reasons)
        )

    @property
    def is_red(self) -> bool:
        return self.count > 0


def run_all(
    root: "str | os.PathLike[str]",
    *,
    allow: Mapping[str, str] | None = None,
    patterns=DEFAULT_WIRING_PATTERNS,
    wide: bool = False,
    marker: str = ".bak_",
    section_re: str = DEFAULT_SECTION_RE,
    skip=DEFAULT_SKIP,
    test_dir_names: Iterable[str] = DEFAULT_TEST_DIR_NAMES,
) -> Report:
    """四つの検出器（＋広い網は任意）を同じ木に当てる。"""
    root = Path(root)
    dirs = tuple(test_dir_names)
    rep = Report(root=root)
    rep.bad_allow_reasons = check_allow_reasons(allow)
    rep.orphans = find_orphans(root, patterns=patterns, allow=allow, skip=skip, test_dir_names=dirs)
    if wide:  # 広い網は、狭い網が既に名指しした物を二度数えない
        wide_found = find_all_orphans(root, allow=allow, skip=skip, test_dir_names=dirs)
        rep.wide_orphans = {n: loc for n, loc in wide_found.items() if n not in rep.orphans}
    rep.empty_test_files = find_empty_test_files(root, skip=skip, backup_marker=marker)
    rep.unmatched_fences = find_unmatched_fences(root, test_dir_names=dirs, skip=skip, backup_marker=marker)
    rep.importable_backups = find_importable_backups(root, marker=marker, skip=skip)
    rep.present_tense_claims = find_present_tense_claims(
        root, section_re=section_re, skip=skip, backup_marker=marker
    )
    return rep


def format_report(rep: Report) -> str:
    """人が読む形。各検出器の件数と、一件ずつの場所。"""
    r = rep.root
    lines = [f"rye_fences: {r}"]

    def section(title: str, items: list[str]) -> None:
        lines.append(f"[{title}] {len(items)}")
        lines.extend(f"  {it}" for it in items)

    if rep.bad_allow_reasons:
        section("allow-without-reason", [f"{n}  (reason too short)" for n in rep.bad_allow_reasons])
    section(
        "orphans: wiring-shaped function, no caller",
        [f"{n}  {loc}" for n, loc in sorted(rep.orphans.items())],
    )
    if rep.wide_orphans is not None:
        section(
            "orphans (wide net): public function, no caller, beyond the wiring patterns",
            [f"{n}  {loc}" for n, loc in sorted(rep.wide_orphans.items())],
        )
    section("empty test files: named like a test, collects nothing", [rel(p, r) for p in rep.empty_test_files])
    section("unmatched fences: asserts, but pytest never picks the file", [rel(p, r) for p in rep.unmatched_fences])
    section("importable backups: backup still ends in .py", [rel(p, r) for p in rep.importable_backups])
    section(
        "present-tense claims: report says it is running now",
        [f"{rel(c.path, r)}:{c.line_no}  {c.text}" for c in rep.present_tense_claims],
    )
    lines.append(f"RED: {rep.count} finding(s)" if rep.is_red else "GREEN: nothing found")
    return "\n".join(lines)


def parse_allow(items: Iterable[str]) -> dict[str, str]:
    """--allow NAME=REASON の列を辞書へ。= が無ければ ValueError。"""
    allow: dict[str, str] = {}
    for item in items:
        name, sep, reason = item.partition("=")
        if not sep or not name.strip():
            raise ValueError(f"--allow expects NAME=REASON, got {item!r}")
        allow[name.strip()] = reason.strip()
    return allow


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="rye_fences",
        description="Count the shapes that never turn red: orphan receivers, test files that "
        "collect nothing, importable backups, present-tense liveness claims.",
    )
    ap.add_argument("root", help="directory to scan")
    ap.add_argument(
        "--allow", action="append", default=[], metavar="NAME=REASON",
        help="intentionally uncalled receiver; the reason must be at least 10 characters",
    )
    ap.add_argument(
        "--pattern", action="append", default=None, metavar="REGEX",
        help="wiring-shaped name regex (repeatable; replaces the defaults)",
    )
    ap.add_argument("--ja", action="store_true", help="also use the Japanese wiring-name patterns")
    ap.add_argument(
        "--wide", action="store_true",
        help="also run the wide net (every public module-level function)",
    )
    ap.add_argument("--marker", default=".bak_", help="backup marker in file names (default: .bak_)")
    ap.add_argument(
        "--section-re", default=DEFAULT_SECTION_RE,
        help="Markdown heading regex whose section is checked for present-tense claims",
    )
    ap.add_argument(
        "--skip", default=None, metavar="REGEX",
        help="path regex to skip (replaces the default skip list)",
    )
    ap.add_argument(
        "--tests-dir", action="append", default=None, metavar="NAME",
        help="directory name treated as a test location (repeatable; default: tests)",
    )
    return ap


def main(argv: list[str] | None = None) -> int:
    ap = build_parser()
    ns = ap.parse_args(argv)
    try:  # 見つけた行に端末が書けない字が在っても落ちない（字は置き換える）
        sys.stdout.reconfigure(errors="backslashreplace")
    except (AttributeError, ValueError):
        pass
    root = Path(ns.root)
    if not root.is_dir():
        print(f"rye_fences: not a directory: {root}", file=sys.stderr)
        return 2
    try:
        allow = parse_allow(ns.allow)
    except ValueError as e:
        print(f"rye_fences: {e}", file=sys.stderr)
        return 2
    patterns = tuple(ns.pattern) if ns.pattern else DEFAULT_WIRING_PATTERNS
    if ns.ja:
        patterns = tuple(patterns) + OPTIONAL_JA_PATTERNS
    rep = run_all(
        root,
        allow=allow,
        patterns=patterns,
        wide=ns.wide,
        marker=ns.marker,
        section_re=ns.section_re,
        skip=ns.skip if ns.skip is not None else DEFAULT_SKIP,
        test_dir_names=tuple(ns.tests_dir) if ns.tests_dir else DEFAULT_TEST_DIR_NAMES,
    )
    print(format_report(rep))
    return 1 if rep.is_red else 0
