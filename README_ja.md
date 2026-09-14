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
（`bench/`）があります。時間もメモリもこのパッケージが負けています — 計測済みの差であって、
主張ではありません。

## パースできないファイルを読む

`symbols-recovered` を提供するパッケージです。厳密な `symbols` がファイルを拒否したときに
[hew](https://github.com/O6lvl4/hew) が使う契約。失敗した文は同じインデントの次の論理行まで、
未終端の文字列や f-string はそれを閉じる行末まで、閉じていない括弧はファイル末尾まで、迷子の
`)` や `$` はその行末までスキップし、スキップした範囲はそれぞれ `ERROR` ノードになります。
文書には byte 範囲がエラーと交差しない宣言だけを、その範囲とともに列挙します。読み手は損傷の
両側にある無傷のメソッドを選べ、壊れたヘッダの下で無傷に見える宣言を選ぶことは決してありません。
書きかけの宣言ヘッダは決して出力しません。このパッケージだけがこの機能を掲げ、他はまだ掲げない
理由がそれです。

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
