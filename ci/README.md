# Reproducible checks

Run `bash ci/check.sh` from a checkout with Almide installed, or set
`ALMIDE_BIN` to an absolute compiler path. `python3` must be CPython 3.14, or
`PYTHON` must name one: the package is checked against CPython itself — its
tokenizer, its standard library and its Unicode 16 tables — and the tokenizer
changed in 3.12, so an older interpreter turns these checks into a token diff
that looks like a gramide defect and is not one. The script says so before it
runs anything.

The run: `almide test`, the package's own binary built from `cli/main.almd`,
a failure if `src/table.almd` is not what the grammar compiles to, the
binary's smoke test, then the oracles. Each `ci/python_*.py` with a
`ci/python_*_probe.almd` beside it builds that probe against the package
(`almide build ci/x_probe.almd`), feeds it cases as JSON and compares the
answers with CPython's; the rest drive the built binary. No model API or
credentials are used. `scripts/gen_python_identifiers.py --check` holds
`src/identifier_data.almd` to CPython's Unicode tables.

CI pins Almide to `dff9a458f2e581631bb6537c856a7974036e4153` and Rust to
`1.94.0`, and installs CPython 3.14. Upgrade these deliberately and rerun the
checks together. `bench/` holds the comparisons against tree-sitter-python and
the generated edit corpus; each script's header says how to build the
reference.
