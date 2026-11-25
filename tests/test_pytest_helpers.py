# -*- coding: utf-8 -*-
"""一行で置ける柵の柵: 赤で AssertionError を出し、緑で何も出さない。"""
from __future__ import annotations

import pytest

from rye_fences import (
    Report,
    assert_all_fences,
    assert_allow_has_reasons,
    assert_no_empty_test_files,
    assert_no_importable_backups,
    assert_no_orphans,
    assert_no_present_tense_claims,
    assert_no_unmatched_fences,
)

HELPERS = [
    pytest.param(assert_no_orphans, "on_start_pipeline", id="orphans"),
    pytest.param(assert_no_empty_test_files, "tests/test_nothing.py", id="empty-test-files"),
    pytest.param(assert_no_importable_backups, "pkg/thing.bak_20250101.py", id="importable-backups"),
    pytest.param(assert_no_present_tense_claims, "docs/report.md:9", id="present-tense"),
]


@pytest.mark.parametrize("helper,needle", HELPERS)
def test_helper_raises_on_the_planted_tree_and_names_the_fake(helper, needle, sample_tree):
    with pytest.raises(AssertionError) as ei:
        helper(sample_tree)
    assert needle in str(ei.value)


@pytest.mark.parametrize("helper,needle", HELPERS)
def test_helper_is_silent_on_the_clean_tree(helper, needle, clean_tree):
    helper(clean_tree)


def test_unmatched_fences_helper(write_tree, clean_tree):
    assert_no_unmatched_fences(clean_tree)
    root = write_tree({"tests/checks.py": "def check_it():\n    assert 1\n"})
    with pytest.raises(AssertionError) as ei:
        assert_no_unmatched_fences(root)
    assert "tests/checks.py" in str(ei.value)


def test_short_allow_reason_fails_before_scanning(sample_tree):
    with pytest.raises(AssertionError) as ei:
        assert_no_orphans(sample_tree, allow={"on_start_pipeline": "short"})
    assert "reason" in str(ei.value)
    with pytest.raises(AssertionError):
        assert_allow_has_reasons({"x": ""})
    assert_allow_has_reasons({"x": "a reason long enough to mean something"})


def test_written_allow_reason_lets_the_orphan_through(sample_tree):
    assert_no_orphans(sample_tree, allow={"on_start_pipeline": "called by the scheduler through its config"})


def test_wide_option_on_the_helper(sample_tree):
    with pytest.raises(AssertionError) as ei:
        assert_no_orphans(
            sample_tree,
            allow={"on_start_pipeline": "called by the scheduler through its config"},
            wide=True,
        )
    assert "helper_unused" in str(ei.value)


def test_assert_all_fences(sample_tree, clean_tree):
    rep = assert_all_fences(clean_tree)
    assert isinstance(rep, Report) and rep.count == 0
    with pytest.raises(AssertionError) as ei:
        assert_all_fences(sample_tree)
    assert "RED: 5 finding(s)" in str(ei.value)
