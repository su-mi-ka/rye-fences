# -*- coding: utf-8 -*-
"""rye_fences — テストはライ麦畑の柵。

崖から落ちそうな子供を掴まえる者の柵。柵は遊び方を教えない。「ここから先は崖だ」だけを言う。
テストは仕様書ではなく、**これまでに落ちた回数の記録**だ。

ここに在るのは、例外も出ず・テストも通るのに壊れている「赤くならない形」を AST で数える検出器:

  一. 柵の形をしていて、一度も走らない       → find_empty_test_files / find_unmatched_fences
  二. 退避が本体ツリーに残り import されうる  → find_importable_backups
  三. 受け口が在るのに呼び手が居ない          → find_orphans / find_all_orphans
  四. 報告書が「いま走っている」と現在形で書く → find_present_tense_claims

自分の pytest に一行で置くなら rye_fences.pytest_helpers、手で当てるなら python -m rye_fences <root>。
"""
from __future__ import annotations

from ._walk import (
    DEFAULT_SKIP,
    DEFAULT_TEST_DIR_NAMES,
    DEFAULT_TEST_FILE_PATTERNS,
    scan_tree,
    skip_also,
)
from .cli import Report, format_report, run_all
from .orphans import (
    DEFAULT_WIRING_PATTERNS,
    MIN_REASON_LEN,
    OPTIONAL_JA_PATTERNS,
    Census,
    check_allow_reasons,
    find_all_orphans,
    find_orphans,
    take_census,
)
from .present_tense import (
    DEFAULT_CLAIM_RE,
    DEFAULT_PAST_RE,
    DEFAULT_SECTION_RE,
    Claim,
    find_present_tense_claims,
)
from .pytest_helpers import (
    assert_all_fences,
    assert_allow_has_reasons,
    assert_no_empty_test_files,
    assert_no_importable_backups,
    assert_no_orphans,
    assert_no_present_tense_claims,
    assert_no_unmatched_fences,
)
from .stray_backups import find_importable_backups
from .zero_collect import collected_names, find_empty_test_files, find_unmatched_fences, has_assert

__version__ = "0.1.0"

__all__ = [
    "Census",
    "Claim",
    "DEFAULT_CLAIM_RE",
    "DEFAULT_PAST_RE",
    "DEFAULT_SECTION_RE",
    "DEFAULT_SKIP",
    "DEFAULT_TEST_DIR_NAMES",
    "DEFAULT_TEST_FILE_PATTERNS",
    "DEFAULT_WIRING_PATTERNS",
    "MIN_REASON_LEN",
    "OPTIONAL_JA_PATTERNS",
    "Report",
    "assert_all_fences",
    "assert_allow_has_reasons",
    "assert_no_empty_test_files",
    "assert_no_importable_backups",
    "assert_no_orphans",
    "assert_no_present_tense_claims",
    "assert_no_unmatched_fences",
    "check_allow_reasons",
    "collected_names",
    "find_all_orphans",
    "find_empty_test_files",
    "find_importable_backups",
    "find_orphans",
    "find_present_tense_claims",
    "find_unmatched_fences",
    "format_report",
    "has_assert",
    "run_all",
    "scan_tree",
    "skip_also",
    "take_census",
]
