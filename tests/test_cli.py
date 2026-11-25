# -*- coding: utf-8 -*-
"""CLI の柵: 終了コードと出力の形。python -m rye_fences も実プロセスで一度通す。"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from rye_fences import Report, format_report, run_all
from rye_fences.cli import main, parse_allow

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_exit_1_on_the_planted_tree_and_0_on_the_clean_tree(sample_tree, clean_tree, capsys):
    assert main([str(sample_tree)]) == 1
    out = capsys.readouterr().out
    assert "RED:" in out and "on_start_pipeline" in out and "tests/test_nothing.py" in out
    assert "pkg/thing.bak_20250101.py" in out and "docs/report.md:9" in out
    assert main([str(clean_tree)]) == 0
    assert "GREEN: nothing found" in capsys.readouterr().out


def test_exit_2_on_bad_arguments(tmp_path, capsys):
    assert main([str(tmp_path / "missing")]) == 2
    assert main([str(tmp_path), "--allow", "noequals"]) == 2
    assert "NAME=REASON" in capsys.readouterr().err


def test_allow_with_a_written_reason_silences_the_orphan(sample_tree, capsys):
    rc = main([str(sample_tree), "--allow", "on_start_pipeline=called by the scheduler through its config"])
    out = capsys.readouterr().out
    assert rc == 1  # 他の偽物はまだ在る
    assert "[orphans: wiring-shaped function, no caller] 0" in out


def test_allow_with_a_short_reason_is_itself_a_finding(clean_tree, capsys):
    assert main([str(clean_tree), "--allow", "on_start_pipeline=short"]) == 1
    assert "allow-without-reason" in capsys.readouterr().out


def test_ja_adds_the_japanese_patterns(write_tree, capsys):
    root = write_tree({"pkg/bake.py": "def 起動時に焼く():\n    return 1\n"})
    assert main([str(root)]) == 0
    capsys.readouterr()
    assert main([str(root), "--ja"]) == 1
    assert "起動時に焼く" in capsys.readouterr().out


def test_pattern_replaces_the_defaults(write_tree, capsys):
    root = write_tree({"pkg/x.py": "def on_start_x():\n    return 1\n\ndef boot_y():\n    return 2\n"})
    assert main([str(root), "--pattern", r"^boot_.+"]) == 1
    out = capsys.readouterr().out
    assert "boot_y" in out and "on_start_x" not in out


def test_wide_reports_only_beyond_the_narrow_net(sample_tree, capsys):
    main([str(sample_tree), "--wide"])
    out = capsys.readouterr().out
    assert "[orphans (wide net): public function, no caller, beyond the wiring patterns] 1" in out
    assert "helper_unused" in out


def test_tests_dir_option(write_tree, capsys):
    root = write_tree({"spec/checks.py": "def check_it():\n    assert 1\n"})
    assert main([str(root)]) == 0
    capsys.readouterr()
    assert main([str(root), "--tests-dir", "spec"]) == 1


def test_parse_allow():
    assert parse_allow(["a=reason one", " b = reason two "]) == {"a": "reason one", "b": "reason two"}
    with pytest.raises(ValueError):
        parse_allow(["=no name"])


def test_report_counts_and_format(sample_tree, clean_tree):
    rep = run_all(sample_tree)
    assert isinstance(rep, Report) and rep.is_red and rep.count == 5
    assert rep.wide_orphans is None
    assert format_report(rep).splitlines()[-1] == "RED: 5 finding(s)"
    green = run_all(clean_tree, wide=True)
    assert not green.is_red and green.wide_orphans == {}
    assert format_report(green).splitlines()[-1] == "GREEN: nothing found"


def _run(*args: str) -> subprocess.CompletedProcess:
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONUTF8": "1"}
    return subprocess.run(
        [sys.executable, "-m", "rye_fences", *args],
        cwd=REPO_ROOT, env=env, capture_output=True, text=True, encoding="utf-8", timeout=120,
    )


def test_python_m_rye_fences_exit_codes(sample_tree, clean_tree, tmp_path):
    assert _run(str(sample_tree)).returncode == 1
    assert _run(str(clean_tree)).returncode == 0
    assert _run(str(tmp_path / "missing")).returncode == 2


def test_demo_runs_and_prints_both_verdicts():
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONUTF8": "1"}
    cp = subprocess.run(
        [sys.executable, str(REPO_ROOT / "examples" / "demo.py")],
        cwd=REPO_ROOT, env=env, capture_output=True, text=True, encoding="utf-8", timeout=120,
    )
    assert cp.returncode == 1  # sample_tree は赤であるべきなので 1
    assert "RED: 6 finding(s)" in cp.stdout and "GREEN: nothing found" in cp.stdout
