# -*- coding: utf-8 -*-
"""形その二の柵: 退避が本体ツリーに残っていて import されうる。"""
from __future__ import annotations

from fnmatch import fnmatch

import pytest

from rye_fences import DEFAULT_SKIP, find_importable_backups, skip_also
from rye_fences._walk import rel


def _rels(paths, root):
    return {rel(p, root) for p in paths}


def test_backup_ending_in_py_is_found_and_extension_smashed_one_is_not(write_tree):
    root = write_tree({
        "pkg/x.bak_20250101.py": "VALUE = 1\n",       # 拾われる
        "pkg/x.py.bak_20250101": "VALUE = 1\n",       # 作法どおり（拡張子まで潰してある）
        "pkg/x.py": "VALUE = 2\n",
    })
    assert _rels(find_importable_backups(root), root) == {"pkg/x.bak_20250101.py"}


def test_custom_marker_and_suffix(write_tree):
    root = write_tree({
        "pkg/x.orig_1.py": "VALUE = 1\n",
        "pkg/y.bak_1.pyi": "VALUE: int\n",
    })
    assert find_importable_backups(root) == []
    assert _rels(find_importable_backups(root, marker=".orig_"), root) == {"pkg/x.orig_1.py"}
    assert _rels(find_importable_backups(root, suffix=".pyi"), root) == {"pkg/y.bak_1.pyi"}


def test_empty_marker_is_refused(tmp_path):
    with pytest.raises(ValueError):
        find_importable_backups(tmp_path, marker="")


def test_skipped_directories_are_not_scanned(write_tree):
    root = write_tree({
        "build/x.bak_1.py": "VALUE = 1\n",
        "quarantine/y.bak_1.py": "VALUE = 1\n",
        "attic/z.bak_1.py": "VALUE = 1\n",
    })
    assert _rels(find_importable_backups(root), root) == {"attic/z.bak_1.py"}
    assert find_importable_backups(root, skip=skip_also(DEFAULT_SKIP, "attic")) == []


def test_the_hazard_is_real_pytest_default_glob_matches_backup_of_a_test_file():
    """崖の記録: test_*.py は test_x.bak_20250101.py にも当たる。古い柵が走る。"""
    assert fnmatch("test_x.bak_20250101.py", "test_*.py")
    assert not fnmatch("test_x.py.bak_20250101", "test_*.py")
