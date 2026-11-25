# -*- coding: utf-8 -*-
"""形その一の柵: 柵の形をしていて、一度も走らない。"""
from __future__ import annotations

import ast

import pytest

from rye_fences import collected_names, find_empty_test_files, find_unmatched_fences, has_assert
from rye_fences._walk import rel


def _rels(paths, root):
    return {rel(p, root) for p in paths}


@pytest.mark.parametrize(
    "source,expected",
    [
        ("def test_a():\n    pass\n", ["test_a"]),
        ("async def test_b():\n    pass\n", ["test_b"]),
        ("class TestX:\n    def test_c(self):\n        pass\n", ["TestX"]),
        ("class Fence:\n    pass\n", []),
        ("async def run_it():\n    pass\n", []),
        # unittest: Test 接頭辞が無くても TestCase の子で test* メソッドを持てば収集される（元の柵 2026-10-16）
        ("import unittest\nclass Fence(unittest.TestCase):\n    def test_read(self): pass\n", ["Fence"]),
        ("from unittest import TestCase as Case\nclass Fence(Case):\n    def test_read(self): pass\n", ["Fence"]),
        ("import unittest\nclass Fence(unittest.IsolatedAsyncioTestCase):\n    async def test_read(self): pass\n", ["Fence"]),
        ("import unittest as ut\nclass Fence(ut.TestCase):\n    def test_read(self): pass\n", ["Fence"]),
        # TestCase の子でも test* メソッドが無ければ何も走らない
        ("import unittest\nclass Fence(unittest.TestCase):\n    def helper(self): pass\n", []),
        # 孫クラスも TestCase
        ("import unittest\nclass Base(unittest.TestCase):\n    pass\nclass Fence(Base):\n    def test_read(self): pass\n", ["Fence"]),
    ],
)
def test_collected_names_matches_pytest_defaults(source, expected):
    assert collected_names(ast.parse(source)) == expected


def test_has_assert_sees_nested_asserts():
    assert has_assert(ast.parse("def f():\n    if 1:\n        assert 2\n"))
    assert not has_assert(ast.parse("def f():\n    return 1\n"))


def test_empty_test_file_is_found_and_real_one_is_not(write_tree):
    root = write_tree({
        "tests/test_nothing.py": "async def run_it():\n    return 1\n",
        "tests/test_real.py": "def test_x():\n    assert True\n",
        "tests/also_test.py": "def helper():\n    return 1\n",   # *_test.py も拾われる名
    })
    assert _rels(find_empty_test_files(root), root) == {"tests/test_nothing.py", "tests/also_test.py"}


def test_empty_test_file_anywhere_in_the_tree_counts(write_tree):
    root = write_tree({"tools/test_probe.py": "def probe():\n    return 1\n"})
    assert _rels(find_empty_test_files(root), root) == {"tools/test_probe.py"}


def test_backup_named_test_files_belong_to_the_other_detector(write_tree):
    root = write_tree({"tests/test_old.bak_20250101.py": "def helper():\n    return 1\n"})
    assert find_empty_test_files(root) == []


def test_syntax_error_is_loud_already_so_not_counted(write_tree):
    root = write_tree({"tests/test_broken.py": "def (:\n"})
    assert find_empty_test_files(root) == []


def test_custom_patterns(write_tree):
    root = write_tree({"tests/check_x.py": "def helper():\n    return 1\n"})
    assert find_empty_test_files(root) == []
    assert _rels(find_empty_test_files(root, patterns=("check_*.py",)), root) == {"tests/check_x.py"}


def test_unmatched_fence_in_tests_dir_is_found(write_tree):
    root = write_tree({
        "tests/checks.py": "def check_it():\n    assert 1 == 1\n",          # assert 持ち・名前が拾われない
        "tests/probe.py": "def test_like():\n    return 1\n",              # test* 関数持ち・名前が拾われない
        "tests/tool.py": "def measure():\n    return 1\n",                 # 計器（assert 無し）→ 通る
        "tests/conftest.py": "import pytest\nassert pytest\n",             # 免除
        "tests/__init__.py": "",
        "src/checks.py": "def check():\n    assert True\n",                # tests/ の外 → 見ない
    })
    assert _rels(find_unmatched_fences(root), root) == {"tests/checks.py", "tests/probe.py"}


def test_unmatched_fence_respects_custom_test_dir_names(write_tree):
    root = write_tree({"spec/checks.py": "def check_it():\n    assert 1\n"})
    assert find_unmatched_fences(root) == []
    assert _rels(find_unmatched_fences(root, test_dir_names=("spec",)), root) == {"spec/checks.py"}
