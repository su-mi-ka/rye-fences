# -*- coding: utf-8 -*-
"""偽物を植えた木と、きれいな木に、同じ検出器を当てて件数を出す。

    python examples/demo.py

sample_tree は四つの形を一つずつ植えてある（＋広い網だけが掴む一つ）。
clean_tree は全部 0 件になる。**緑は検出器の証拠にならない**ので、
偽物の側が赤くなることを先に見る。
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))  # 置いただけで動くように（pip install 不要）

from rye_fences import format_report, run_all  # noqa: E402


def main() -> int:
    worst = 0
    for name in ("sample_tree", "clean_tree"):
        rep = run_all(HERE / name, wide=True)
        print(format_report(rep).replace(str(HERE / name), f"examples/{name}"))
        print()
        worst = max(worst, 1 if rep.is_red else 0)
    print("sample_tree must be RED and clean_tree must be GREEN for the detectors to mean anything.")
    return worst


if __name__ == "__main__":
    sys.exit(main())
