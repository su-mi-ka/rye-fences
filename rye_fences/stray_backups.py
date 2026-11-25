# -*- coding: utf-8 -*-
"""形その二: **退避が本体ツリーに残っていて、import されうる。**

退避の作法は「拡張子まで潰す」——x.py.bak_<理由>_<日時> は誰にも拾われない。
x.bak_<理由>_<日時>.py の形で置いた日から、拾う物が出てくる:

  - pytest の既定 test_*.py は test_x.bak_20250101.py にも当たる（* が . を跨ぐ）。
    古い柵が走り、新しい柵と二重に、あるいは食い違って赤くなる。
  - *.py を glob して自動登録する仕組み（プラグイン・ツールの読み込み）が拾う。
  - 同じ物が二つ在って片方が孤児——次の者が死んでいる方へ繋ぐ。

★ 元のリポジトリの実測（2026-09-08）: 本体ツリーの .bak_* は 988 件、うち *.py.bak_* が 881 件。
  *.bak_*.py は **0 件**だった。この 0 を守るのがこの柵。
"""
from __future__ import annotations

import os
from pathlib import Path

from ._walk import DEFAULT_SKIP, scan_tree


def find_importable_backups(
    root: "str | os.PathLike[str]",
    marker: str = ".bak_",
    skip=DEFAULT_SKIP,
    suffix: str = ".py",
) -> list[Path]:
    """名に marker を含みつつ suffix で終わるファイル＝import / pytest / glob が拾いうる退避。"""
    if not marker:
        raise ValueError("marker must be a non-empty string")
    return [p for p in scan_tree(root, skip, suffixes=(suffix,)) if marker in p.name]
