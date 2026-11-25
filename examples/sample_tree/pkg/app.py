# -*- coding: utf-8 -*-
"""偽物を植えた木。四つの「赤くならない形」を一つずつ置いてある。

この木は import しても例外を出さず、pytest を当てても赤くならない。
だから検出器が要る。
"""


def on_start_pipeline():
    """形その三（狭い網）: 配線の形をした受け口。誰も呼ばない。"""
    return "started"


def helper_unused():
    """形その三（広い網だけが掴む）: 公開関数だが呼び手が無い。"""
    return 1


def build():
    return render()


def render():
    return "ok"
