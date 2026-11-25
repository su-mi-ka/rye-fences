# -*- coding: utf-8 -*-
"""木を歩く共通の物差し。

四つの検出器が**同じ足で同じ木を歩く**ために一箇所に置く。
歩き方が検出器ごとに違うと、片方だけ直る日が来る（「同じ工程が二箇所以上に散っている」も
赤くならない形の一つ）。
"""
from __future__ import annotations

import ast
import os
import re
from fnmatch import fnmatch
from pathlib import Path
from typing import Iterable

#: 触らない所。退避・隔離・キャッシュ・仮想環境・第三者コード・ビルド成果物。
#: 元の柵はここに所有者の退避フォルダ名（日本語）も入れていた。自分の名前は skip_also で足す。
DEFAULT_SKIP: re.Pattern[str] = re.compile(
    r"(^|[\/])(__pycache__|\.git|\.hg|\.svn|\.venv|venv|\.tox|\.nox|\.mypy_cache"
    r"|\.pytest_cache|\.ruff_cache|node_modules|site-packages|build|dist|\.eggs"
    r"|quarantine|_quarantine|_backup|_backups)([\/]|$)"
)

#: pytest がファイル名で拾う形（python_files を上書きしていない既定）。
DEFAULT_TEST_FILE_PATTERNS: tuple[str, ...] = ("test_*.py", "*_test.py")

#: テストの置き場として扱うディレクトリ名。
DEFAULT_TEST_DIR_NAMES: tuple[str, ...] = ("tests",)


def compile_skip(skip: "re.Pattern[str] | str | None") -> re.Pattern[str] | None:
    """skip を正規表現へ揃える。None なら何も避けない。"""
    if skip is None:
        return None
    if isinstance(skip, str):
        return re.compile(skip)
    return skip


def skip_also(base: "re.Pattern[str] | str | None", *dir_names: str) -> re.Pattern[str]:
    """既定の避け方に、自分のディレクトリ名を足した正規表現を返す。

    >>> skip_also(DEFAULT_SKIP, "examples", "fixtures")
    """
    names = "|".join(re.escape(n) for n in dir_names)
    extra = rf"(^|[\/])({names})([\/]|$)" if names else ""
    pat = compile_skip(base)
    if pat is None:
        return re.compile(extra or r"(?!)")
    return re.compile(f"{pat.pattern}|{extra}" if extra else pat.pattern)


def scan_tree(
    root: "str | os.PathLike[str]",
    skip: "re.Pattern[str] | str | None" = DEFAULT_SKIP,
    suffixes: tuple[str, ...] = (".py",),
) -> list[Path]:
    """root の下のファイルを、避ける所を刈りながら拾って返す（並びは決定的）。

    避けるかどうかは **root からの相対パス**で見る。root 自身がどんな名前の場所に
    置かれていても（たとえば build/ の中）、中身は全部歩く。
    """
    root = Path(root)
    pat = compile_skip(skip)
    out: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        rel_dir = os.path.relpath(dirpath, root)
        if rel_dir == ".":
            rel_dir = ""
        keep = []
        for d in sorted(dirnames):
            if pat is not None and pat.search(os.path.join(rel_dir, d)):
                continue
            keep.append(d)
        dirnames[:] = keep
        for f in sorted(filenames):
            if not f.endswith(suffixes):
                continue
            if pat is not None and pat.search(os.path.join(rel_dir, f)):
                continue
            out.append(Path(dirpath, f))
    return out


def parse_python(path: "str | os.PathLike[str]") -> ast.Module | None:
    """読めない・構文の壊れたファイルは None。

    構文の壊れたファイルは import の時点で**赤くなる**ので、この柵の相手ではない。
    バイト列で渡すのは PEP 263 の coding 宣言を ast に任せるため。
    """
    try:
        with open(path, "rb") as fh:
            return ast.parse(fh.read(), filename=str(path))
    except (OSError, SyntaxError, ValueError):
        return None


def read_text(path: "str | os.PathLike[str]") -> str | None:
    """UTF-8 で読む。読めない所は捨てる（報告書は読めれば足りる）。"""
    try:
        with open(path, encoding="utf-8", errors="ignore") as fh:
            return fh.read()
    except OSError:
        return None


def rel(path: "str | os.PathLike[str]", root: "str | os.PathLike[str]") -> str:
    """root からの相対パスを / 区切りで返す（報告に書く形）。"""
    return os.path.relpath(path, root).replace("\\", "/")


def is_test_path(
    rel_posix: str,
    test_dir_names: Iterable[str] = DEFAULT_TEST_DIR_NAMES,
    file_patterns: Iterable[str] = DEFAULT_TEST_FILE_PATTERNS,
) -> bool:
    """tests/ の下か、test_*.py の名か。pytest が呼び手になる場所。"""
    parts = rel_posix.split("/")
    names = set(test_dir_names)
    if any(p in names for p in parts[:-1]):
        return True
    return any(fnmatch(parts[-1], pat) for pat in file_patterns)
