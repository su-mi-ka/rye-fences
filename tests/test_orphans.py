# -*- coding: utf-8 -*-
"""形その三の柵: 受け口が在るのに呼び手が居ない。

元の柵が踏んだ穴（as 名だけ数えて元の名を落とした・tests/ を数えて赤が常態化した）を、ここで杭にする。
"""
from __future__ import annotations

import re

import pytest

from rye_fences import (
    DEFAULT_SKIP,
    OPTIONAL_JA_PATTERNS,
    check_allow_reasons,
    find_all_orphans,
    find_orphans,
    skip_also,
    take_census,
)

HOOK = "def wire_things():\n    return 1\n"


def test_wiring_shaped_function_without_caller_is_an_orphan(write_tree):
    root = write_tree({"pkg/hooks.py": HOOK})
    assert find_orphans(root) == {"wire_things": "pkg/hooks.py:1"}


def test_decorated_function_is_not_counted(write_tree):
    """@register の類は名前で呼ばれない配線。呼び手が居ないのが正しい形。"""
    root = write_tree({
        "pkg/hooks.py": """
            def register(fn):
                return fn

            @register
            def wire_things():
                return 1
        """
    })
    assert find_orphans(root) == {}


def test_called_by_bare_name_is_not_an_orphan(write_tree):
    root = write_tree({
        "pkg/hooks.py": HOOK,
        "pkg/boot.py": "from pkg.hooks import wire_things\n\nwire_things()\n",
    })
    assert find_orphans(root) == {}


def test_called_through_attribute_is_not_an_orphan(write_tree):
    root = write_tree({
        "pkg/hooks.py": HOOK,
        "pkg/boot.py": "from pkg import hooks\n\nhooks.wire_things()\n",
    })
    assert find_orphans(root) == {}


def test_from_import_as_counts_the_original_name(write_tree):
    """from m import f as g は f の呼び手でもある（元の柵が 2026-10-08 に塞いだ穴）。"""
    root = write_tree({
        "pkg/hooks.py": HOOK,
        "pkg/boot.py": "from pkg.hooks import wire_things as w\n\nw()\n",
    })
    assert find_orphans(root) == {}


def test_import_module_as_counts_the_last_component(write_tree):
    """import a.b.c as x は c を参照に数える。"""
    root = write_tree({
        "pkg/run_startup_checks.py": "def run_startup_checks():\n    return 1\n",
        "pkg/boot.py": "import pkg.run_startup_checks as rsc\n\nrsc.run_startup_checks()\n",
    })
    assert find_orphans(root) == {}


def test_method_with_wiring_name_is_counted_and_attribute_call_rescues_it(write_tree):
    root = write_tree({
        "pkg/svc.py": """
            class Service:
                def on_start_listening(self):
                    return 1
        """
    })
    assert set(find_orphans(root)) == {"on_start_listening"}
    (root / "pkg" / "boot.py").write_text("from pkg.svc import Service\n\nService().on_start_listening()\n", encoding="utf-8")
    assert find_orphans(root) == {}


def test_test_functions_in_tests_dir_are_not_receivers(write_tree):
    """test_startup_hook の _hook はアプリのフックではない。pytest が呼び手。"""
    root = write_tree({
        "tests/test_boot.py": "def test_startup_hook():\n    assert True\n",
        "test_toplevel.py": "def test_other_hook():\n    assert True\n",
    })
    assert find_orphans(root) == {}


def test_non_test_helper_in_tests_dir_is_still_a_receiver(write_tree):
    root = write_tree({"tests/helpers.py": "def wire_fake():\n    return 1\n"})
    assert set(find_orphans(root)) == {"wire_fake"}


def test_reference_from_a_test_counts_as_a_caller(write_tree):
    """参照は木の全部から集める。テストだけが呼ぶ受け口も「呼び手が居る」。それでよいかは使う側の判断。"""
    root = write_tree({
        "pkg/hooks.py": HOOK,
        "tests/test_hooks.py": "from pkg.hooks import wire_things\n\ndef test_it():\n    assert wire_things() == 1\n",
    })
    assert find_orphans(root) == {}


def test_allow_hides_the_name(write_tree):
    root = write_tree({"pkg/hooks.py": HOOK})
    assert find_orphans(root, allow={"wire_things": "wired by the plugin loader through a config file"}) == {}


def test_allow_reasons_must_be_written():
    bad = check_allow_reasons({"a": "short", "b": "", "c": "a reason long enough to mean something"})
    assert bad == ["a", "b"]
    assert check_allow_reasons(None) == []
    assert check_allow_reasons({"x": "exactly 10"}, min_len=10) == []


def test_string_constant_does_not_rescue_in_the_narrow_net_unless_asked(write_tree):
    root = write_tree({
        "pkg/hooks.py": HOOK,
        "pkg/boot.py": "import importlib\n\nfn = getattr(importlib.import_module('pkg.hooks'), 'wire_things')\n",
    })
    assert set(find_orphans(root)) == {"wire_things"}
    assert find_orphans(root, strings_count_as_refs=True) == {}


def test_japanese_patterns_are_optional(write_tree):
    root = write_tree({"pkg/bake.py": "def 起動時に焼く():\n    return 1\n"})
    assert find_orphans(root) == {}
    assert set(find_orphans(root, patterns=OPTIONAL_JA_PATTERNS)) == {"起動時に焼く"}


def test_patterns_accept_a_single_regex_or_compiled(write_tree):
    root = write_tree({"pkg/x.py": "def boot_everything():\n    return 1\n"})
    assert set(find_orphans(root, patterns=r"^boot_.+")) == {"boot_everything"}
    assert set(find_orphans(root, patterns=re.compile(r"^boot_.+"))) == {"boot_everything"}


def test_wide_net_catches_what_the_narrow_net_lets_through(write_tree):
    """狭い網が緑なのは、崖が無いからではない。"""
    root = write_tree({
        "pkg/util.py": """
            def helper_unused():
                return 1

            def _private_unused():
                return 2

            def main():
                return 3

            def test_like():
                return 4
        """
    })
    assert find_orphans(root) == {}
    assert set(find_all_orphans(root)) == {"helper_unused"}


def test_wide_net_skips_definitions_in_tests_and_decorated(write_tree):
    root = write_tree({
        "tests/helpers.py": "def make_thing():\n    return 1\n",
        "pkg/reg.py": """
            def register(fn):
                return fn

            @register
            def plugin_entry():
                return 1
        """,
    })
    assert find_all_orphans(root) == {}  # register は plugin_entry 経由で参照されている・make_thing は tests/


def test_wide_net_counts_string_constants_by_default(write_tree):
    root = write_tree({
        "pkg/util.py": "def helper_unused():\n    return 1\n",
        "pkg/wiring.py": "ENTRY = 'helper_unused'\n",
    })
    assert find_all_orphans(root) == {}
    assert set(find_all_orphans(root, strings_count_as_refs=False)) == {"helper_unused"}


def test_skipped_directories_are_neither_definitions_nor_callers(write_tree):
    root = write_tree({
        "pkg/hooks.py": HOOK,
        ".venv/lib/site.py": "def wire_venv():\n    return 1\n",
        "build/caller.py": "from pkg.hooks import wire_things\nwire_things()\n",
    })
    assert set(find_orphans(root)) == {"wire_things"}  # build/ の呼び手は数えない・.venv の定義も数えない


def test_skip_also_adds_a_directory(write_tree):
    root = write_tree({
        "pkg/hooks.py": HOOK,
        "fixtures/caller.py": "from pkg.hooks import wire_things\nwire_things()\n",
    })
    assert find_orphans(root) == {}
    assert set(find_orphans(root, skip=skip_also(DEFAULT_SKIP, "fixtures"))) == {"wire_things"}


def test_unparseable_file_is_ignored_not_fatal(write_tree):
    root = write_tree({
        "pkg/hooks.py": HOOK,
        "pkg/broken.py": "def (:\n",
    })
    census = take_census(root)
    assert {p.name for p in census.trees} == {"hooks.py"}
    assert set(find_orphans(root)) == {"wire_things"}
