# rye-fences — 赤くならない壊れ方を、AST で数える柵

## Summary (English)

- "Tests are the fence in the rye field": a fence does not teach how to play, it only says "the cliff starts here".
- Four detectors for shapes that **never turn red**: no exception, every test green, and still broken.
  1. **Fences that never run:** files named like tests that collect nothing, and files with asserts that pytest never picks up.
  2. **Importable backups:** `x.bak_20250101.py` left in the tree, picked up by `test_*.py` globs or plugin loaders.
  3. **Orphan receivers:** wiring-shaped functions (`on_start_*`, `*_hook`, …) that nobody calls. A wide net checks every public module-level function.
  4. **Present-tense liveness claims:** a report that says "the daemon is running" in the present tense, which reads as a fact long after it stopped being one.
- Use it as a CLI (`python -m rye_fences <root>`, exit code 1 when anything is found) or as one-line pytest fences (`assert_no_orphans("src")`).
- Intentional receivers go into an allow list **with a reason** of at least 10 characters; an allow entry without a reason is a removed fence.
- Standard library only, Python 3.11+. 88 pytest tests, including planted fakes and a self-check on its own tree.

## 何か

テストが全部緑なのに壊れている、という形を機械で数える道具です。見つける形は四つあります。

| 形 | 何が起きているか | 検出器 |
|---|---|---|
| 一. 柵の形をしていて、一度も走らない | `test_` で始まるのに 0 件しか集まらない。逆に assert が在るのに pytest に拾われない | `find_empty_test_files`・`find_unmatched_fences` |
| 二. 退避が import されうる | `x.bak_<日時>.py` が `test_*.py` やプラグインの読み込みに拾われる | `find_importable_backups` |
| 三. 受け口が在るのに呼び手が居ない | 関数は在るが誰も呼ばない。例外もテストの赤も出ない | `find_orphans`・`find_all_orphans` |
| 四. 報告書が現在形で「走っている」と書く | 書かれた時は本当でも、読む時には嘘になっている | `find_present_tense_claims` |

## なぜ注目に値するか

普通のテストは「壊れたら赤くなる」物しか掴まえません。ここに並ぶ四つは、どれも壊れても赤くならない形です。

- 元の運用では、一件の孤児を直した後に木を全部数え直して、同じ形がさらに三件見つかりました。一件目を直した時点では、残りは一つも見えていませんでした。
- テスト名を持つのに一件も集めないファイルは、全員が「その柵は在る」と思っている間、一行も走っていませんでした。
- 報告書の「本体は走行中」は、書かれた時点で既に止まっていた本体のことでした。

だから人の目や掟ではなく、数える機械を置きます。

## どう動くか

- **二つの網:** `find_orphans` は配線の形をした名前だけを見る狭い網です。`find_all_orphans` は module 直下の公開関数を全部見る広い網です。狭い網が緑でも、崖が無いとは限りません。
- **収集の見立ては pytest の既定に合わせます:** module 直下の `test*` 関数、`Test*` クラス、`unittest.TestCase` のサブクラスを数えます。
- **退避の作法:** `x.py.bak_<理由>_<日時>` のように拡張子まで潰せば、誰にも拾われません。この形は通し、`.py` で終わる退避だけを数えます。
- **現在形の見張り:** Markdown の決まった節の中だけを読み、コードブロックは読みません。縛るのは時刻の有無ではなく、現在形で閉じていないかです。

## 使い方

```bash
python -m rye_fences examples/sample_tree    # 植えた五件が出て RED、終了コード 1
python -m rye_fences examples/clean_tree     # GREEN、終了コード 0
python -m rye_fences src --wide --allow on_start_debug="手で呼ぶ診断の入口として置いている"
```

自分のリポジトリの pytest に一行で置く形です。

```python
from rye_fences.pytest_helpers import assert_no_orphans

def test_every_receiver_has_a_caller():
    assert_no_orphans("src")
```

`AssertionError` を明示的に投げるので、`python -O` でも消えません。

## 出所

ある自作の AI エージェントの運用で、2026-09-08 から置いてきた柵を、どのリポジトリにも当てられる形に切り出しました。四つの形は、どれも実際に踏んでから柵にした物です。

## 柵

```bash
python -m pytest -q
```

2026-11-21 の観測で 88 passed です。検出器ごとの柵に加えて、わざと植えた偽物を全部見つけることと、この道具自身の木が緑であることを確かめています。

## 未了

- 狭い網の既定の名前の形は、元の運用に合わせてあります。ほかのリポジトリでは `--pattern` で足すのが前提です。
- ライセンス: [MIT](LICENSE)
