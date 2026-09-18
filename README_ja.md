# gramide-python

[gramide-cli](https://github.com/O6lvl4/gramide-cli) の Python 3.14。自前の字句解析器、値としての文法、
その文法をコンパイルした表、どのノードが名前を宣言するかの規則、そして編集途中のファイルにも
読み手が答えられるようにする回復。ひとつの Almide パッケージ `gramide_python` で、依存は
[gramide](https://github.com/O6lvl4/gramide) だけです。`gramide` コマンド（[gramide-cli](https://github.com/O6lvl4/gramide-cli)）はこれを出荷し、
このリポジトリはこれ単体を CPython と照合し、計測し、リリースする場所です。

[English](README.md)

```
almide build cli/main.almd -o gramide_python       # .py と .pyi だけの gramide
./gramide_python check $(python3.14 -c 'import sysconfig;print(sysconfig.get_path("stdlib"))')/*.py
./gramide_python outline inspect.py                # `L2-3 method A.m`。入れ子は `Outer.Inner.method`
./gramide_python symbols-recovered editing.py      # 壊れていない宣言と、壊れている場所
./gramide_python gen-table > src/table.almd        # 文法を変えたら
```

## カバー範囲

パッケージはコミット `23116f998f6789d8c2fbe5ed5b8146854c8c2a4f` の CPython v3.14.4 の文法と
字句解析器に従い、そのすべてを `ci/` のオラクルで CPython 3.14 自身（tokenizer、`ast`、コンパイラ、
Unicode 16 の表）と照合しています。このリリースで `bash ci/check.sh` が検証するもの:

| 段階 | CPython 3.14 との照合 |
|---|---|
| レイアウト（indent/dedent スタック、タブ、formfeed、行継続、括弧） | 有効 25 ケース、拒否 51 ケース |
| 通常文字列の境界 | 2,020 境界と拒否 12 |
| 数値 | 650 境界と拒否 32 |
| 識別子 | 全 1,114,112 コードポイントの両クラスと UTF-8 スキャン 38 |
| f-string・t-string を含む字句解析器全体 | 受理 409、拒否 11、標準ライブラリ 12 ファイルをトークン単位で |
| 式 | AST 構造一致 2,993、拒否 3,037 |
| 文・宣言・match パターン | 木の一致 857、拒否 1,600、標準ライブラリ 12 ファイル完全版を本体まで |
| 宣言の名前・所有者・範囲 | 入れ子・デコレータ付き・async・スタブ・12 ファイルにわたる 645 宣言 |
| 定義と参照（`tags`） | 報告するケース 12、意図的に報告しないケース 6 |
| 回復: 論理行、文字列、補間、括弧、孤立エラー | 55・163・239・160・102 ケース。いずれも厳密な `check` は拒否のまま |

`check` は文法検査であって、CPython がそのファイルをコンパイルできる保証ではありません。
コンパイラ文脈の規則（重複パラメータ、`async` 外の `await`、内包変数を束縛し直す walrus）、
`\N{…}` エスケープ、NFKC の名前同一性、リテラルの復号、エンコーディングクッキーと BOM は
未実装です。[docs/progress.md](docs/progress.md) は各段階をどう作り、各オラクルが何を
カバーするかの記録で、`docs/evidence/` にはコーパスのハッシュと tree-sitter-python との比較
（`bench/`）があります。新規プロセスでの `inspect.py` のアウトラインは tree-sitter の 0.70 倍の時間、
標準ライブラリ 15 ファイル中 11 で速く、負ける 4 つは数 KB のファイルで、負荷時のプロセスの床の
差です（[証拠](docs/evidence/python-outline-rows.json)）。メモリは今も tree-sitter が上で、
インクリメンタルパースはありません。

## パースできないファイルを読む

`symbols-recovered` を提供するパッケージです。厳密な `symbols` がファイルを拒否したときに
[hew](https://github.com/O6lvl4/hew) が使う契約。失敗した文は同じインデントの次の論理行まで、
未終端の文字列や f-string(置換フィールドの `}` が消えた場合も)は、引用符 1 つで
開いたものならその行末まで、3 つなら
ファイル末尾まで、閉じていない括弧は開いた行と同じかそれより浅いインデントで文が始まる行まで(より深く
開いている種類の閉じ括弧はそこまで閉じる)、迷子の `)` や `$` はその行末までスキップし、スキップした範囲はそれぞれ `ERROR` ノードになります。
文書には byte 範囲がエラーと交差しない宣言だけを、その範囲とともに列挙します。読み手は損傷の
両側にある無傷のメソッドを選べ、壊れたヘッダの下で無傷に見える宣言を選ぶことは決してありません。
書きかけの宣言ヘッダは決して出力しません。このパッケージだけがこの機能を掲げ、他はまだ掲げない
理由がそれです。

エディタの中のファイルは壊れていることの方が多い。`bench/recovery.py` はコーパスの全ファイルを
4 通りに 1 箇所ずつ壊し(単語の頭に `{` を打つ、`}` を消す、`)` を消す、`(` を打つ)、
各ツールがまだ列挙できるもの(gramide は回復パースの上の `outline`、tree-sitter は同じ
ハーネスの `--recover` で木から)を、そのツール自身の無傷のファイルでの列挙と、種別・名前・
開始行で比べる。壊した箇所を含む宣言が消えるのは当然で、それ以外を失わず余計なものも出さ
なかった破壊を「きれい」と数える([証拠](docs/evidence/recovery-cpython-stdlib.json)、[仕組み](https://github.com/O6lvl4/gramide/blob/main/docs/recovery.md)):

| CPython `Lib/`: 1,450 ファイル、5,193 回の破壊 | gramide | tree-sitter |
|---|---:|---:|
| 残った宣言(全破壊) | 99.0% | 96.3% |
| きれいに回復した破壊(壊した箇所以外を失わず、余計なものも出さない) | 98.2% | 82.3% |
| きれいに回復、`insert {` | 98.7% | 92.3% |
| きれいに回復、`delete }` | 96.7% | 73.0% |
| きれいに回復、`delete )` | 97.3% | 68.9% |
| きれいに回復、`insert (` | 99.3% | 91.1% |

4 通りすべてで gramide が上。gramide が失うのは壊した箇所を含む文だけで、tree-sitter は `}` や `)` を
消すとその周りのブロックを失う。f-string の置換フィールドから `}` が消えた場合は gramide も
ファイルの残り全部を失っていたが、引用符 1 つで開いた文字列はその行で終わる、とスキャナが
覚えてからは 1 文で済む。

## キー入力 1 回

エディタはファイルではなく編集をパーサに渡します。エンジンはパース済みのファイルを recover item
（ここでは先頭レベルと各スイートの中の各文。このパッケージが回復の単位にしているのが文だからです）
の入れ子として持ち、編集が触れた最小の item を読み直します。トークンに触れない編集や名前 1 つの
打ち直しは何も読みません（[仕組み](https://github.com/O6lvl4/gramide/blob/main/docs/incremental.md)）。
同じ 1,000 編集（13 文字以上の単語の 6 文字目に 1 文字打つ・消す）を、gramide の `reparse-bench` と、
tree-sitter-python `26855ea` の `ts_tree_edit`＋再パース
（[gramide-javascript](https://github.com/O6lvl4/gramide-javascript/blob/main/bench/tree_sitter_ranges.c) の
C ハーネスを `-DLANG=tree_sitter_python` で組んだもの）にプロセス内で与え、50 回に 1 回は丸ごとの
パースと照合しました（[証拠](docs/evidence/incremental-python-argparse.json)、`bench/incremental.py`）。

| 1,000 編集、中央値 / 90 パーセンタイル | gramide | tree-sitter | 丸ごとのパース |
|---|---:|---:|---:|
| `argparse.py`（100 KB） | 5.4 / 8.4 µs | 44 / 65 µs | 2.6 ms |
| `typing.py`（130 KB） | 11 / 15 µs | 112 / 129 µs | 3.1 ms |

各 item は ID を持ち、その item に触れない編集では変わりません。この 2,000 編集で ID が変わった item は
ゼロでした。標準ライブラリ（`lib/python3.14` 配下の `test`・`lib2to3`・`idlelib` 以外の全 `.py`）のうち
十分長い単語を持つ 1,300 ファイルに各 10 回のランダム編集（13,000 回、毎回トークンとノードを丸ごとの
パースと照合）で差はゼロ、ファイル全体の読み直しもゼロでした
（[証拠](docs/evidence/incremental-corpus-cpython-stdlib.json)）。`ci/incremental_check.py` がこれを回し、
1 回の編集は `reparse --edit START:OLD_END:NEW_END --new FILE` です。

## 書き方

- **`src/lexer.almd`** と `layout`・`strings`・`interpolation`・`escapes`・`numbers`・
  `identifiers`・`identifier_data` — CPython の `Parser/lexer` に沿ってモジュールごとに書いた
  字句解析器。物理トークン、次にそれを CPython のインデントと代替インデントのスタックで論理的な
  `newline`・`indent`・`dedent` マーカーに変えるレイアウト段階、f/t-string のモードスタック、
  CPython 自身の表から `scripts/gen_python_identifiers.py` が生成する Unicode 16 の識別子クラス。
- **`src/grammar.almd`** は `statements`・`compounds`・`declarations`・`patterns`・`expressions`・
  `containers`・`comprehensions`・`lambdas`・`parameters`・`arguments`・`string_expressions` に
  またがって組まれた文法の入口を名指しします。それぞれ `Grammar/python.gram` の対応する節に
  従います。文のリストはエンジンの `recover_lines` を使います。
- **`src/symbols.almd`** — 関数・クラス・型エイリアスが名前を宣言し、クラスがメソッドを所有し、
  入れ子の宣言は語彙的なパス `Outer.Inner.method` を持つので、hew が同名の宣言を選べます。
- **`src/table.almd`** — `gen-table` の生成物。古ければ CI が落ちます。

## 検査

`bash ci/check.sh` には CPython 3.14 が必要です（`python3` が別の版なら `PYTHON=python3.14`。
スクリプトは他の版ではオラクルを走らせず、理由を言います）。`almide test`、表の一致検査、
バイナリのスモーク、上の表のすべてのオラクルを走らせます（[ci/README.md](ci/README.md)）。

## ライセンス

MIT または Apache-2.0、お好みで。
