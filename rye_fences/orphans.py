# -*- coding: utf-8 -*-
"""形その三: **受け口が在るのに、呼び手が居ない。**

関数は在る。誰も呼ばない。例外は出ないし、テストも通る——呼ばれないだけだ。
機械で数える以外に見つける方法が無い。

★ この柵が生まれた実測（元のリポジトリ・2026-09-08）

  1. 起動時に焼く処理の受け口が**どこからも呼ばれていなかった。**
     「焼き待ちに置いた」の印だけが溜まり、焼き物は一枚も出ていなかった。
  2. run_startup_preflight() — 同じ形。しかもモジュールの説明が「起動はこれを通る」と
     読ませていた。実際の起動は別の場所が一つずつ呼んでおり、この集約口は本番より弱い別物だった。
  3. register_bot_turn() — bot 同士の無限ループを止める保険層。**モジュールごと import 0 件。**
     生きた実体は別ファイルに在り、同じ物が二つ在って片方が孤児だった。

  ⚠ 一件目を直した時点で、二・三件目は一つも見えていなかった。見えたのは AST で木を
    **全部数え直してから**だ（一件直したら同じ形を全部狩る＝サーチアンドデストロイ）。

★ 二つの網

  - find_orphans     … **狭い網。**「配線の形をした名前」（on_start_* / wire_* / *_hook …）だけを見る。
                        全関数を見ると雑音になる、という元の判断を保つ。
  - find_all_orphans … **広い網。**module 直下の公開関数を全部見る。
                        元のリポジトリでは狭い網が 5 passed で緑のまま、広い網が 35 件を数えた。
                        **狭い網が緑なのは、崖が無いからではない。**

★ 意図して置く受け口は allow に**理由つきで**足す（check_allow_reasons）。
  理由の無い追加は柵を外すのと同じ。
"""
from __future__ import annotations

import ast
import os
import re
from pathlib import Path
from typing import Iterable, Mapping, NamedTuple

from ._walk import (
    DEFAULT_SKIP,
    DEFAULT_TEST_DIR_NAMES,
    DEFAULT_TEST_FILE_PATTERNS,
    is_test_path,
    parse_python,
    rel,
    scan_tree,
)

#: **配線の形をした名前。**「呼ばれて初めて意味が在る」種類——受け口・起動フック・登録口。
DEFAULT_WIRING_PATTERNS: tuple[str, ...] = (
    r"^on_start.*",      # on_start, on_startup, on_start_pipeline
    r"^on_stop.*",       # on_stop, on_stop_pipeline
    r"^on_shutdown.*",
    r"^run_startup.*",   # run_startup_preflight（元の実測の二件目）
    r"^wire_.+",         # wire_handlers
    r".+_hook$",         # startup_hook, before_send_hook
)

#: 元のリポジトリが日本語の関数名に使っていた形。日本語で書く木では足す。
OPTIONAL_JA_PATTERNS: tuple[str, ...] = (
    r"^(起動時に|停止時に).+",
    r".+(を促す|を配線|へ移る|を繋ぐ)$",
)

#: 広い網でも数えない名前。名前で呼ばれない入口。
DEFAULT_IGNORE_NAMES: re.Pattern[str] = re.compile(r"^(main|run|setup|cli|app)$")

#: allow の理由に要る最低の長さ。短い理由は「赤いから足した」の印。
MIN_REASON_LEN = 10


def compile_patterns(patterns) -> tuple[re.Pattern[str], ...]:
    """文字列・正規表現・その列、どれで渡されても正規表現の組へ揃える。"""
    if isinstance(patterns, (str, re.Pattern)):
        patterns = (patterns,)
    return tuple(p if isinstance(p, re.Pattern) else re.compile(p) for p in patterns)


class Census(NamedTuple):
    """木を一度歩いた結果。定義側と参照側で二度歩かないために持つ。"""

    trees: dict[Path, ast.Module]
    refs: set[str]      # Name / Attribute / import alias として現れた名前
    strings: set[str]   # 文字列定数（getattr や設定ファイル経由の配線）


def take_census(root, skip=DEFAULT_SKIP) -> Census:
    """木の全 .py を読み、「この木で参照されている名前」の集合を作る。

    - ast.Name … 裸の名前（呼び出し・代入・引き渡し）
    - ast.Attribute … mod.name / obj.name の name 側
    - ast.alias … from m import f as g は **f の呼び手でもある**。asname だけ数えると
      as で呼ばれた関数が孤児に見える（元の柵の側に在った穴・2026-10-08 に塞いだ形を保つ）。
      import a.b.c は最後の要素 c を参照とみなす。
    """
    trees: dict[Path, ast.Module] = {}
    refs: set[str] = set()
    strings: set[str] = set()
    for p in scan_tree(root, skip):
        t = parse_python(p)
        if t is None:
            continue
        trees[p] = t
        for n in ast.walk(t):
            if isinstance(n, ast.Attribute):
                refs.add(n.attr)
            elif isinstance(n, ast.Name):
                refs.add(n.id)
            elif isinstance(n, ast.alias):
                refs.add((n.asname or n.name).rpartition(".")[2])
                refs.add(n.name.rpartition(".")[2])
            elif isinstance(n, ast.Constant) and isinstance(n.value, str):
                strings.add(n.value)
    return Census(trees, refs, strings)


def _functions(tree: ast.Module, *, module_level_only: bool):
    nodes = tree.body if module_level_only else ast.walk(tree)
    for n in nodes:
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            yield n


def find_orphans(
    root: "str | os.PathLike[str]",
    patterns=DEFAULT_WIRING_PATTERNS,
    allow: Mapping[str, str] | None = None,
    skip=DEFAULT_SKIP,
    test_dir_names: Iterable[str] = DEFAULT_TEST_DIR_NAMES,
    test_file_patterns: Iterable[str] = DEFAULT_TEST_FILE_PATTERNS,
    strings_count_as_refs: bool = False,
) -> dict[str, str]:
    """**狭い網。**配線の形をした名前を持つ関数（module 直下もクラス内も）で、
    木のどこからも参照されていない物を {名前: "相対パス:行"} で返す。

    - 飾り（デコレータ）の付いた関数は数えない。@app.on_event や @register は
      「名前で呼ばれない配線」なので、呼び手が居ないのが正しい形。
    - テストの置き場（tests/ と test_*.py）の test* 関数は数えない。pytest が呼び手。
      test_startup_hook の _hook はアプリのフックではない。
    - allow に在る名前は返さない（理由の確認は check_allow_reasons で別に行う）。
    - 参照は木の全ファイルから集める（テストも含む）。テストだけが呼んでいる受け口も
      「呼び手が居る」と数える。それでよいかは使う側の判断。
    """
    pats = compile_patterns(patterns)
    census = take_census(root, skip)
    allowed = set(allow or {})
    defs: dict[str, str] = {}
    for p, t in census.trees.items():
        r = rel(p, root)
        in_tests = is_test_path(r, test_dir_names, test_file_patterns)
        for fn in _functions(t, module_level_only=False):
            if in_tests and fn.name.startswith("test"):
                continue
            if fn.decorator_list:
                continue
            if not any(pt.match(fn.name) for pt in pats):
                continue
            defs.setdefault(fn.name, f"{r}:{fn.lineno}")
    refs = census.refs | (census.strings if strings_count_as_refs else set())
    return {name: loc for name, loc in defs.items() if name not in allowed and name not in refs}


def find_all_orphans(
    root: "str | os.PathLike[str]",
    allow: Mapping[str, str] | None = None,
    skip=DEFAULT_SKIP,
    test_dir_names: Iterable[str] = DEFAULT_TEST_DIR_NAMES,
    test_file_patterns: Iterable[str] = DEFAULT_TEST_FILE_PATTERNS,
    ignore: re.Pattern[str] | str = DEFAULT_IGNORE_NAMES,
    strings_count_as_refs: bool = True,
) -> dict[str, str]:
    """**広い網。**module 直下の公開関数を全部見る。

    数えない物:
      - _ で始まる名前（private と dunder）。使われない private は linter の仕事。
      - test で始まる名前と、テストの置き場にあるファイルの定義（pytest が呼び手）。
      - 飾りの付いた関数（名前で呼ばれない配線）。
      - ignore に当たる名前（main / run / setup … 名前で呼ばれない入口）。
    文字列定数に現れる名前は既定で参照に数える（getattr / 設定ファイル経由の配線を逃がす）。
    """
    ign = re.compile(ignore) if isinstance(ignore, str) else ignore
    census = take_census(root, skip)
    allowed = set(allow or {})
    refs = census.refs | (census.strings if strings_count_as_refs else set())
    out: dict[str, str] = {}
    for p, t in census.trees.items():
        r = rel(p, root)
        if is_test_path(r, test_dir_names, test_file_patterns):
            continue
        for fn in _functions(t, module_level_only=True):
            if fn.name.startswith("_") or fn.name.startswith("test"):
                continue
            if fn.decorator_list or ign.match(fn.name):
                continue
            if fn.name in allowed or fn.name in refs:
                continue
            out.setdefault(fn.name, f"{r}:{fn.lineno}")
    return out


def check_allow_reasons(allow: Mapping[str, str] | None, min_len: int = MIN_REASON_LEN) -> list[str]:
    """理由が無い・短い allow の名前を返す。空文字の理由で通すのは柵を外すのと同じ。"""
    bad = []
    for name, reason in (allow or {}).items():
        if not isinstance(reason, str) or len(reason.strip()) < min_len:
            bad.append(name)
    return bad
