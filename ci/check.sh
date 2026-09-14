#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
compiler="${ALMIDE_BIN:-almide}"
python="${PYTHON:-python3}"

# The package is checked against CPython itself, and which CPython is not a
# detail: its tokenizer changed in 3.12 (a line continuation alone on a line no
# longer swallows the indentation after it), and the identifier oracle is pinned
# to Unicode 16, which is 3.14's. On an older interpreter these checks fail with
# a token diff that looks like a gramide bug and is not one. Say so first.
"$python" -c 'import sys
v = sys.version_info
assert v[:2] == (3, 14), (
    "ci: the oracles are CPython 3.14 — its tokenizer, its stdlib and its Unicode 16 "
    "tables. python here is %d.%d; a failure below would be that difference, not a "
    "defect. Point PYTHON at a 3.14." % (v.major, v.minor))'

"$compiler" test
"$compiler" build cli/main.almd --release -o gramide_python
./gramide_python gen-table | diff -u src/table.almd - \
  || { echo "src/table.almd is not what the grammar compiles to: ./gramide_python gen-table > src/table.almd"; exit 1; }
"$python" ci/smoke.py
"$python" ci/python_layout.py
"$python" ci/python_strings.py
"$python" ci/python_numbers.py
"$python" scripts/gen_python_identifiers.py --check
"$python" ci/python_identifiers.py
"$python" ci/python_lexer.py
"$python" ci/python_lexer_diagnostics.py
"$python" ci/python_expressions.py
"$python" ci/python_statements.py
"$python" ci/python_symbols.py
"$python" ci/python_tags.py
"$python" ci/python_recovery.py
"$python" ci/python_string_recovery.py
"$python" ci/python_interpolation_recovery.py
"$python" ci/python_delimiter_recovery.py
"$python" ci/python_isolated_errors.py
"$python" ci/recovered_symbols.py
"$python" ci/recovery_comparison.py

# A per-file ratchet, not a target. Each file is held where it stands, so a
# clean one cannot rot up to the worst one. Numbers only ever fall;
# --write-baseline records a fall.
if command -v codopsy-almd >/dev/null; then cx=codopsy-almd
elif command -v codopsy_almd >/dev/null; then cx=codopsy_almd
else cx=""; fi
if [ -n "$cx" ]; then
  "$cx" --quiet --baseline .codopsy-almd.json src/
else
  echo "codopsy-almd not on PATH: structural check skipped (almide install github.com/O6lvl4/codopsy-almd)"
fi
