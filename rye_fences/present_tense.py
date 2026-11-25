# -*- coding: utf-8 -*-
"""形その四: **報告書が「いま走っている」と現在形で書く。**

★ この柵が生まれた実測（元のリポジトリ・2026-09-08）

  実施報告の「環境の事実」の節が「本体は走行中（14:03:24 起動）」と書いていた。書かれたのは 15:20 頃。
  本体は 14:33:36 に落ちていた。
  ⚠ **日付が無かったのではない。書いてあったのに、現在形だったから今の事実に見えた。**
    括弧の中は起動時刻であって観測時刻ではない。
  ★ 正しい形は同じリポジトリに既に二つ在った——「着手時 本体は稼働中（11:37 起動）**だった**」。
    過去形で閉じ、観測時刻を添える。

  「数字には観測時刻を添えろ」は掟として既に書いてあった。書いてあったのに踏んだ。
  だから掟では止まらない——**数える機械が要る。**

★ 縛るのは「時刻が在るか」ではない。**現在形で閉じていないか**だ。
  見るのは Markdown の該当する節（見出しから次の見出しまで）の中だけ。コードブロックは読まない。
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import NamedTuple

from ._walk import DEFAULT_SKIP, read_text, scan_tree

#: この見出しの節だけを見る（大文字小文字は区別しない）。
DEFAULT_SECTION_RE = r"環境の事実|Environment facts"

#: 現在形の生存。
DEFAULT_CLAIM_RE = (
    r"(走行中|稼働中|起動中|走っている|動いている|生きている"
    r"|is running|are running|still running|currently running|up and running"
    r"|running\)?\.?\s*$)"
)

#: 過去形へ閉じてある印・観測時刻の印。どれか一つ在れば、読む者が今の事実として掴む危険は無い。
DEFAULT_PAST_RE = (
    r"(だった|でした|であった|当時|時点|着手時|観測|落ち|畳|止ま|未確認"
    r"|was running|were running|had been running|at the time|as of |observed)"
)


class Claim(NamedTuple):
    """現在形で生存を主張している一行。"""

    path: Path
    line_no: int
    text: str


def iter_section_lines(text: str, section_re: re.Pattern[str]):
    """Markdown 本文から、該当する見出しの節の行を (行番号, 行) で返す。

    節は「当たる見出し」から「次の見出し」まで。フェンス付きコードブロックは飛ばす。
    """
    in_section = False
    in_code = False
    for i, line in enumerate(text.splitlines(), 1):
        if line.strip().startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        if line.startswith("#"):
            in_section = bool(section_re.search(line))
            continue
        if in_section:
            yield i, line


def find_present_tense_claims(
    root: "str | os.PathLike[str]",
    section_re: str | re.Pattern[str] = DEFAULT_SECTION_RE,
    claim_re: str | re.Pattern[str] = DEFAULT_CLAIM_RE,
    exclude_past_re: str | re.Pattern[str] | None = DEFAULT_PAST_RE,
    skip=DEFAULT_SKIP,
    suffixes: tuple[str, ...] = (".md",),
    backup_marker: str | None = ".bak_",
) -> list[Claim]:
    """該当する節の中で、現在形の生存を主張し、過去形へ閉じていない行を返す。"""
    sec = re.compile(section_re, re.IGNORECASE) if isinstance(section_re, str) else section_re
    claim = re.compile(claim_re) if isinstance(claim_re, str) else claim_re
    past = re.compile(exclude_past_re) if isinstance(exclude_past_re, str) else exclude_past_re
    out: list[Claim] = []
    for p in scan_tree(root, skip, suffixes=suffixes):
        if backup_marker and backup_marker in p.name:
            continue
        text = read_text(p)
        if text is None:
            continue
        for i, line in iter_section_lines(text, sec):
            if not claim.search(line):
                continue
            if past is not None and past.search(line):
                continue
            out.append(Claim(p, i, line.strip()[:160]))
    return out
