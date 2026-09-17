# gramide-python

Python 3.14 for [gramide-cli](https://github.com/O6lvl4/gramide-cli): a lexer of its
own, the grammar as a value, that grammar compiled, the rules that say which
of its nodes declare a name, and the recovery that lets a reader answer about
a file that is halfway through being edited — one Almide package,
`gramide_python`, depending on [gramide](https://github.com/O6lvl4/gramide)
and on nothing else. The `gramide` command ([gramide-cli](https://github.com/O6lvl4/gramide-cli)) ships it; this repository is where it is
tested against CPython, measured and released on its own.

[日本語](README_ja.md)

```
almide build cli/main.almd -o gramide_python       # gramide over .py and .pyi alone
./gramide_python check $(python3.14 -c 'import sysconfig;print(sysconfig.get_path("stdlib"))')/*.py
./gramide_python outline inspect.py                # `L2-3 method A.m`; nested: `Outer.Inner.method`
./gramide_python symbols-recovered editing.py      # declarations untouched by the damage, and where the damage is
./gramide_python gen-table > src/table.almd        # after any change to the grammar
```

## What it covers

The package follows the CPython v3.14.4 grammar and lexer at commit
`23116f998f6789d8c2fbe5ed5b8146854c8c2a4f`, and every part of it is checked
against CPython 3.14 itself — its tokenizer, its `ast`, its compiler and its
Unicode 16 tables — by the oracles in `ci/`. What `bash ci/check.sh` verifies,
as of this release:

| stage | against CPython 3.14 |
|---|---|
| layout (indent/dedent stacks, tabs, formfeed, continuations, brackets) | 25 valid and 51 rejected cases |
| ordinary string boundaries | 2,020 boundaries and 12 rejected strings |
| numbers | 650 boundaries and 32 rejected literals |
| identifiers | all 1,114,112 code points, both classes, and 38 UTF-8 scans |
| the whole lexer, f-strings and t-strings included | 409 accepted inputs, 11 rejected, and 12 standard-library files token for token |
| expressions | 2,993 matching AST structures, 3,037 rejected |
| statements, declarations, match patterns | 857 matching trees, 1,600 rejected, 12 complete standard-library files body for body |
| declaration names, owners and ranges | 645 declarations across nested, decorated and async cases, stubs and the 12 files |
| definitions and references (`tags`) | 12 reported cases, and 6 that are deliberately not |
| recovery: logical lines, strings, interpolation, delimiters, isolated errors | 55, 163, 239, 160 and 102 cases, each keeping strict `check` a rejection |

`check` is a grammar check, not a promise that CPython compiles the file:
compiler-context rules (a duplicate parameter, `await` outside `async`, a
walrus rebinding a comprehension variable), `\N{…}` escapes, NFKC name
identity, literal decoding, encoding cookies and BOMs are not implemented.
[docs/progress.md](docs/progress.md) is the record of how each stage was built
and what each oracle covers; `docs/evidence/` holds the corpus hashes and the
comparisons against tree-sitter-python (`bench/`): a fresh-process outline of
`inspect.py` takes 0.70x tree-sitter's time, eleven of fifteen standard
library files read faster, and the four that do not are a few kilobytes each
and lose by the process floor under load ([evidence](docs/evidence/python-outline-rows.json)).
Memory is still tree-sitter's; incremental parsing is not here at all.

## Reading a file that does not parse

This is the package that offers `symbols-recovered`, the contract
[hew](https://github.com/O6lvl4/hew) uses when strict `symbols` refuses a
file. A failed statement is skipped to the next logical line at the same
indentation, an unterminated string or f-string — a `}` gone from a
replacement field included — to the end of its line when it opened with one
quote, to the end of the file when with three, an unclosed bracket to the line where a statement begins at the
opener's indentation or less (a closer of a kind open deeper closes down to
it), a stray `)` or `$` to the end of its line; each skipped range becomes an `ERROR` node. The document
then lists only the declarations whose byte ranges do not intersect an error,
with the ranges themselves, so a reader can select the intact methods on both
sides of the damage and never a declaration that looks intact under a broken
header. A partial declaration head is never exported, which is why this
package advertises the capability and the others do not yet.

An editor's file is broken more often than not. `bench/recovery.py` breaks every
file of the corpus in four ways, one at a time — a `{` typed at the start of a
word, a `}` deleted, a `)` deleted, a `(` typed — and compares what each tool
still lists (gramide's `outline`, which reads the recovered parse; tree-sitter's
tree through the same harness, `--recover`) with its own listing of the whole
file, by kind, name and start line. A declaration whose lines hold the break is
expected to go; a break is *clean* when nothing else is lost and nothing new
appears ([evidence](docs/evidence/recovery-cpython-stdlib.json), [how it recovers](https://github.com/O6lvl4/gramide/blob/main/docs/recovery.md)):

| CPython `Lib/`: 1,450 files, 5,193 breaks | gramide | tree-sitter |
|---|---:|---:|
| declarations kept, all breaks | 98.9% | 96.3% |
| clean breaks (nothing lost beyond the break, nothing invented) | 98.1% | 82.3% |
| clean breaks, `insert {` | 98.7% | 92.3% |
| clean breaks, `delete }` | 96.7% | 73.0% |
| clean breaks, `delete )` | 97.3% | 68.9% |
| clean breaks, `insert (` | 99.2% | 91.1% |

gramide is ahead on every kind of break. What it loses is the statement that
holds the break; what tree-sitter loses on a `}` or `)` deleted is the block
around it, and on a `}` gone from an f-string's field, the rest of the file
was gramide's loss too until the scanner learned that a string opened with
one quote ends on its line.

## One keystroke

An editor hands the parser the edit, not the file. The engine keeps a parsed
file as its recover items — here, every statement, at the top and inside
every suite, since a statement is what this package recovers by — and
re-reads the smallest one an edit touched; an edit that touches no token or
retypes one name reads nothing at all
([how](https://github.com/O6lvl4/gramide/blob/main/docs/incremental.md)).
The same 1,000 edits, each a letter typed or deleted six letters into a word
of thirteen or more, in-process, for gramide's `reparse-bench` and for
tree-sitter-python at `26855ea` through `ts_tree_edit` + reparse in the C
harness of
[gramide-javascript](https://github.com/O6lvl4/gramide-javascript/blob/main/bench/tree_sitter_ranges.c)
built with `-DLANG=tree_sitter_python`; every fiftieth result checked
against a whole parse ([evidence](docs/evidence/incremental-python-argparse.json),
`bench/incremental.py`):

| 1,000 edits, median / 90th percentile | gramide | tree-sitter | a whole parse |
|---|---:|---:|---:|
| `argparse.py` (100 KB) | 5.5 / 8.8 µs | 44 / 66 µs | 2.5 ms |
| `typing.py` (130 KB) | 11 / 15 µs | 112 / 130 µs | 3.1 ms |

Every item carries an id that the edits leaving it alone do not change: over
these 2,000 edits no item was renamed. Over the standard library — every
`.py` under `lib/python3.14` but `test`, `lib2to3` and `idlelib` — ten random
edits in each of the 1,300 files that hold a long enough word (13,000 edits,
every one checked token for token and node for node against a whole parse
of the same text) gave no difference and no whole-file read
([evidence](docs/evidence/incremental-corpus-cpython-stdlib.json)).
`ci/incremental_check.py` runs this; `reparse --edit START:OLD_END:NEW_END --new FILE`
is the one-edit command.

## How it is written

- **`src/lexer.almd`** with `layout`, `strings`, `interpolation`, `escapes`,
  `numbers`, `identifiers` and `identifier_data` — the lexer, module by module
  along CPython's `Parser/lexer`: physical tokens, then the layout stage that
  turns them into logical `newline`, `indent` and `dedent` markers with
  CPython's indentation and alternate-indentation stacks; a mode stack for
  f- and t-strings; Unicode 16 identifier classes generated by
  `scripts/gen_python_identifiers.py` from CPython's own tables.
- **`src/grammar.almd`** names the entry of a grammar composed across
  `statements`, `compounds`, `declarations`, `patterns`, `expressions`,
  `containers`, `comprehensions`, `lambdas`, `parameters`, `arguments` and
  `string_expressions`, each following the matching section of
  `Grammar/python.gram`. Statement lists use the engine's `recover_lines`.
- **`src/symbols.almd`** — functions, classes and type aliases declare names;
  a class owns its methods, and a nested declaration carries its lexical
  path, `Outer.Inner.method`, so hew can select same-named declarations.
- **`src/table.almd`** — generated by `gen-table`; CI fails if it is stale.

## Checks

`bash ci/check.sh` needs CPython 3.14 (`PYTHON=python3.14` if `python3` is
another version; the script refuses to run the oracles on anything else, and
says why). It runs `almide test`, the table check, the binary's smoke test
and every oracle in the table above ([ci/README.md](ci/README.md)).

## License

MIT or Apache-2.0, at your option.
