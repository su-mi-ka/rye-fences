# -*- coding: utf-8 -*-
"""形その四の柵: 報告書が「いま走っている」と現在形で書く。"""
from __future__ import annotations

from rye_fences import Claim, find_present_tense_claims
from rye_fences._walk import rel


def _hits(root, **kw):
    return {(rel(c.path, root), c.line_no) for c in find_present_tense_claims(root, **kw)}


def test_present_tense_inside_the_section_is_found(write_tree):
    root = write_tree({
        "docs/r.md": """
            # 報告
            ## 9-5. 環境の事実
            - 本体は走行中（14:03:24 起動）。
            ## 10. 備考
            - 本体は走行中、と書いてあっても節の外。
        """
    })
    assert _hits(root) == {("docs/r.md", 3)}


def test_past_tense_or_observation_time_closes_the_sentence(write_tree):
    root = write_tree({
        "docs/r.md": """
            ## 環境の事実
            - 着手時、本体は走行中だった（11:37 起動）。
            - 15:42:26 観測 — 本体は落ちたまま。
            - 当時は稼働中。
        """
    })
    assert _hits(root) == set()


def test_english_forms(write_tree):
    root = write_tree({
        "docs/r.md": """
            ## Environment facts
            - The daemon is running (started 14:03).
            - status: running.
            - At 15:42 (observed) the daemon was running.
            - as of 15:42 the worker is running
            - running the tests gave 10 passed
        """
    })
    assert _hits(root) == {("docs/r.md", 2), ("docs/r.md", 3)}


def test_code_blocks_are_not_read(write_tree):
    root = write_tree({
        "docs/r.md": """
            ## 環境の事実
            ```text
            本体は走行中
            ```
            - 本体は走行中
        """
    })
    assert _hits(root) == {("docs/r.md", 5)}


def test_section_heading_matches_case_insensitively_and_can_be_changed(write_tree):
    root = write_tree({
        "docs/r.md": """
            ## ENVIRONMENT FACTS
            - it is running
            ## Runtime
            - it is running
        """
    })
    assert _hits(root) == {("docs/r.md", 2)}
    assert _hits(root, section_re=r"Runtime") == {("docs/r.md", 4)}


def test_custom_claim_and_past_regex(write_tree):
    root = write_tree({
        "docs/r.md": """
            ## 環境の事実
            - サーバは稼働している
            - サーバは稼働していた
        """
    })
    assert _hits(root) == set()
    assert _hits(root, claim_re=r"稼働している", exclude_past_re=r"していた") == {("docs/r.md", 2)}
    assert _hits(root, claim_re=r"稼働してい", exclude_past_re=None) == {("docs/r.md", 2), ("docs/r.md", 3)}


def test_backup_markdown_is_skipped_and_claim_is_a_named_tuple(write_tree):
    root = write_tree({
        "docs/r.md.bak_1.md": "## 環境の事実\n- 本体は走行中\n",
        "docs/r.md": "## 環境の事実\n- 本体は走行中\n",
    })
    claims = find_present_tense_claims(root)
    assert len(claims) == 1
    c = claims[0]
    assert isinstance(c, Claim)
    assert (rel(c.path, root), c.line_no, c.text) == ("docs/r.md", 2, "- 本体は走行中")


def test_a_section_without_claims_is_green(write_tree):
    root = write_tree({"docs/r.md": "## 環境の事実\n- pytest: 10 passed\n"})
    assert find_present_tense_claims(root) == []
