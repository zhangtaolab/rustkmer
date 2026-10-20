---
phase: 04-benchmark-validation
reviewed: 2026-10-20T00:00:00Z
depth: standard
files_reviewed: 115
files_reviewed_list:
  - .github/workflows/ci.yml
  - CONTRIBUTING.md
  - INSTALL.md
  - PROJECT_SUMMARY.md
  - README.md
  - USER_GUIDE.md
  - VERSION.md
  - docs/README.md
  - docs/api-reference/database.md
  - docs/api-reference/exceptions.md
  - docs/api-reference/fuzzyquery.md
  - docs/api-reference/index.md
  - docs/api-reference/kmercounter.md
  - docs/api-reference/overview.md
  - docs/api-reference/python/examples.md
  - docs/api-reference/python/getting-started.md
  - docs/api-reference/python/index.md
  - docs/api-reference/query.md
  - docs/api-reference/rust/args.md
  - docs/api-reference/rust/binary.md
  - docs/api-reference/rust/canonical.md
  - docs/api-reference/rust/count.md
  - docs/api-reference/rust/database.md
  - docs/api-reference/rust/discovery.md
  - docs/api-reference/rust/dump.md
  - docs/api-reference/rust/encoding.md
  - docs/api-reference/rust/exceptions.md
  - docs/api-reference/rust/expansion.md
  - docs/api-reference/rust/fasta.md
  - docs/api-reference/rust/fastq.md
  - docs/api-reference/rust/filtering.md
  - docs/api-reference/rust/format.md
  - docs/api-reference/rust/fuzzy.md
  - docs/api-reference/rust/fuzzy_query.md
  - docs/api-reference/rust/index.md
  - docs/api-reference/rust/kmer_counter.md
  - docs/api-reference/rust/lib.md
  - docs/api-reference/rust/matrix.md
  - docs/api-reference/rust/metadata.md
  - docs/api-reference/rust/mmap.md
  - docs/api-reference/rust/monitoring.md
  - docs/api-reference/rust/mutation.md
  - docs/api-reference/rust/normalization.md
  - docs/api-reference/rust/operations.md
  - docs/api-reference/rust/overflow.md
  - docs/api-reference/rust/performance.md
  - docs/api-reference/rust/persistence.md
  - docs/api-reference/rust/query.md
  - docs/api-reference/rust/table.md
  - docs/api-reference/rust/text.md
  - docs/api-reference/rust/wildcard.md
  - docs/api-reference/stats.md
  - docs/architecture/overview.md
  - docs/examples/advanced.md
  - docs/examples/basic-usage.md
  - docs/examples/batch-processing.md
  - docs/examples/data-export.md
  - docs/examples/database-ops.md
  - docs/examples/fuzzy-search.md
  - docs/examples/merging.md
  - docs/examples/python/README.md
  - docs/examples/statistics.md
  - docs/getting-started/first-steps.md
  - docs/getting-started/index.md
  - docs/getting-started/installation-advanced.md
  - docs/getting-started/installation.md
  - docs/getting-started/troubleshooting.md
  - docs/getting-started/virtual-environments.md
  - docs/guides/CLI_PYO3_FEATURE_COMPARISON.md
  - docs/guides/FINAL_UNIFIED_INTERFACE_REPORT.md
  - docs/guides/benchmarking.md
  - docs/guides/configuration.md
  - docs/guides/development.md
  - docs/guides/hybrid-search-guide.md
  - docs/guides/prefix-query-guide.md
  - docs/guides/pyo3-binding-guide.md
  - docs/guides/pyo3-binding-readme.md
  - docs/guides/testing.md
  - docs/guides/user-guide.md
  - docs/implementation/prefix-query-report.md
  - docs/implementation/streaming-merge-design.md
  - docs/index.md
  - docs/installation.md
  - docs/mkdocs.yml
  - docs/performance/memory-optimization.md
  - docs/troubleshooting/cli-status.md
  - docs/troubleshooting/n-position-demo.md
  - docs/troubleshooting/prefix-extraction-demo.md
  - docs/tutorials/basic-workflow.md
  - docs/tutorials/batch-processing.md
  - docs/tutorials/index.md
  - docs/tutorials/integration.md
  - docs/tutorials/large-genomes.md
  - docs/user-guide/cli.md
  - docs/user-guide/concepts.md
  - docs/user-guide/counter.md
  - docs/user-guide/counting-kmers.md
  - docs/user-guide/error-recovery.md
  - docs/user-guide/examples.md
  - docs/user-guide/fuzzy-search.md
  - docs/user-guide/index.md
  - docs/user-guide/performance-tips.md
  - docs/user-guide/querying.md
  - docs/user-guide/quickstart.md
  - examples/python/demo_fuzzy.py
  - examples/python/demo_fuzzy_enhanced.py
  - examples/python/demo_performance.py
  - examples/python/demo_position_mutations_fixed.py
  - examples/python/demo_pyo3_binding.py
  - examples/python/simple_prefix_query.py
  - examples/python/test_pyo3_api.py
  - examples/python/unified_query_example.py
  - pyo3/pyproject.toml
  - src/io/fastq.rs
  - tests/merge_bounded_memory_tests.rs
findings:
  critical: 0
  warning: 8
  info: 6
  total: 14
status: issues_found
---

# Phase 4: Code Review Report

**Reviewed:** 2026-10-20T00:00:00Z
**Depth:** standard
**Files Reviewed:** 115
**Status:** issues_found

## Summary

Incremental re-review of everything changed in the phase-04 window since the phase's own full review at `3d042f9`: docs churn (~97 regenerated/edited docs), 8 example-script fixes, the `pyo3-pytest` CI job, the pytest addopts change, and quick-task source fixes in `src/io/fastq.rs` and `tests/merge_bounded_memory_tests.rs`.

**Method.** All non-documentation files were read in full. The ~97 doc files were reviewed adversarially but selectively: every CLI command, env var, config claim, and Python API usage in the changed docs was cross-checked against the actual clap definitions (`src/cli/args.rs`, `src/cli/commands/count.rs`) and the actual PyO3 surface (`pyo3/src/{database,counter,prefix_query,fuzzy_query}.rs`); cross-file references (file paths, PyPI projects, guide names) were resolved against the real tree and registry. Every finding below was verified by re-opening the cited source.

**Assessment.** The source-code changes are sound:

- `src/io/fastq.rs` — WR-15/16/17 and IN-12 fixes are correct and well-pinned: `total_sequence_length`/`average_quality` now route through the compression-aware opener; `count_sequences` propagates record errors; `filter_by_quality`'s raw-ASCII semantics are documented; regression tests are meaningful (gzip fixtures with member-count sanity assertions, error-context assertions that avoid flate2-internal wording). No external callers depend on the changed error contract.
- `tests/merge_bounded_memory_tests.rs` — the tautology fix (assert `estimated > 0` before `estimated - 1`) is correct; only cosmetic residue (IN-06).
- `.github/workflows/ci.yml` — the new `pyo3-pytest` job is correctly built: least-privilege (`pull_request`, not `_target`; `contents: read`), per-job cache keys, a cross-shell `--no-index --find-links` wheel install, and a coverage gate whose mechanism checks out (the local `pyo3/coverage.xml` proves `pyrustkmer/__init__.py` is a maturin-generated shim, so `--cov=pyrustkmer --cov-fail-under=80` does measure something real). The job's "stdlib + pytest only" dependency claim matches the actual imports in `pyo3/tests/`.
- `pyo3/pyproject.toml` — removing cov flags from addopts is correct (plain `pytest` no longer requires pytest-cov); comment accurately points at the CI job.
- All 8 example scripts use the real binding surface — every class, method, getter, and keyword argument they touch was verified to exist with matching arity (`PyDatabase`/`LoadMode`, `PyPrefixQuery`, `PyExtendedPrefixQuery`, `PyPrefixQueryMetrics`, `PyFuzzyQuery`, `PyFuzzyResult`, `PyFuzzyMatch`, `PyCounter`, `PyDatabaseStats`).

All 14 findings are in documentation and docs-adjacent config: README ships copy-pasteable commands the CLI rejects, CONTRIBUTING.md describes a CI/coverage regime that was changed later in the same window, `docs/mkdocs.yml` cannot build (nav points at files that do not exist — this will fail the `mkdocs build --strict` docs-deploy job when these commits reach `main`), and two docs' "verify installation" snippet is a Python syntax error.

No Critical findings: no security vulnerabilities (no secrets, no injection, least-privilege CI), no correctness defects in the Rust/Python source under review.

## Narrative Findings (AI reviewer)

### Warnings

### WR-01: README ships eight `count` commands the CLI rejects (positional input)

**File:** `README.md:273`, `README.md:299`, `README.md:305`, `README.md:433`, `README.md:457`, `README.md:471`, `README.md:477`, `README.md:556`
**Issue:** `Commands::Count` (`src/cli/args.rs:19-105`) accepts inputs only via `-i/--input` or `--directory`; it has no positional argument. The following documented commands fail with "unexpected argument":

```bash
rustkmer count -k 21 --threads 8 --sort -o genome.rkdb genome.fa   # L273 — first quick-start command
rustkmer count -k 33 -o large_kmer.rkdb sequences.fa               # L299
rustkmer count -k 64 -o k64_database.rkdb genome.fa                # L305
rustkmer count -k 31 --threads 16 --size 100000000 -L 5 -U 1000 -C -o counts.rkdb reads.fastq  # L433
rustkmer count -k <KMER_SIZE> -o <OUTPUT> [OPTIONS] <INPUT>        # L457 — usage template itself wrong
rustkmer count -k 21 -o genome.rkdb genome.fa                      # L471
rustkmer count -k 21 -C --sort -o genome_canonical.rkdb genome.fa  # L477
rustkmer count -k 21 --sort -o sorted.rkdb input.fa                # L556
```

This window's docs pass converted INSTALL.md and USER_GUIDE.md to the `-i` form, and even fixed line 474 of README itself (`... -o genome_sorted.rkdb -i genome.fa`) — but left the eight commands above in the broken positional form, including the very first command in "基本用法" that a new user copies.
**Fix:** Insert `-i` before each input path (e.g. `rustkmer count -k 21 --threads 8 --sort -o genome.rkdb -i genome.fa`) and change the usage template at L457 to `rustkmer count [OPTIONS] -k <K> -i <INPUT>... -o <OUTPUT>` (matching the already-correct `USER_GUIDE.md` form `rustkmer count [OPTIONS] -k <K> -i <INPUT>... -o <OUTPUT>`).

### WR-02: README documents a nonexistent `--kmer-size` long flag

**File:** `README.md:461`
**Issue:** README's command reference says `-k, --kmer-size <SIZE>`. The clap field is `k` (`src/cli/args.rs:21-22`), so the derived long flag is `--k`, not `--kmer-size` — `rustkmer count --kmer-size 21` errors with "unexpected argument". `docs/guides/hybrid-search-guide.md:249` already uses the correct `--k 19`.
**Fix:** Change to `` `-k, --k <SIZE>` `` (clap's default derivation from the field name).

### WR-03: CONTRIBUTING.md states the opposite of what CI now does (stale within the same review window)

**File:** `CONTRIBUTING.md:46`
**Issue:** Two false claims, both contradicted by files changed in this same window:

1. "CI does not run the Python test suite" — false since commit b6ea0ee added the `pyo3-pytest` job (ubuntu/macos/windows matrix, `pytest tests/ --cov=pyrustkmer ... --cov-fail-under=80`) to `.github/workflows/ci.yml:133-183`. CONTRIBUTING's own "Build and test commands" table (which claims to be "the exact gates CI runs") omits it.
2. "The `pyo3/tests/` suite carries an 80% coverage gate enforced locally by the `--cov-fail-under=80` addopts in `pyo3/pyproject.toml`" — false; this window's pyproject change reduced addopts to `["-v"]` and moved the gate to CI (see pyproject's own comment and `docs/guides/testing.md:27`, which was updated correctly).

A contributor following CONTRIBUTING.md would skip the pyo3 tests believing CI covers only Rust, and would expect a local coverage gate that no longer exists.
**Fix:** Rewrite the paragraph: CI runs a `pyo3-pytest` job on all three OSes (build wheel → install → `pytest tests/` with `--cov=pyrustkmer --cov-fail-under=80` on the command line); local `pytest` in `pyo3/` runs plain with no forced flags; add the `pyo3-pytest` job to the gates table.

### WR-04: docs/mkdocs.yml nav references four files that do not exist — docs build cannot pass

**File:** `docs/mkdocs.yml:89-93`
**Issue:** The `User Guide > Tutorials` nav entries point at `user-guide/tutorials/basic-workflow.md`, `user-guide/tutorials/large-datasets.md`, `user-guide/tutorials/performance.md`, and `user-guide/tutorials/integration.md`. None exist: there is no `docs/user-guide/tutorials/` directory. The real files are `docs/tutorials/basic-workflow.md`, `docs/tutorials/large-genomes.md`, `docs/tutorials/integration.md`, and `docs/user-guide/performance-tips.md` (verified by directory listing). MkDocs hard-errors on nav paths that don't resolve, and the docs workflow builds with `mkdocs build --strict` (`.github/workflows/docs.yml:56`, triggered on PRs to `main` touching `docs/**`) — so the docs deploy job will go red the moment these commits target `main`. (It slipped through because docs.yml only triggers on `main`, not `dev`.) Additionally, `theme.logo`/`theme.favicon` reference `assets/logo.png`/`assets/favicon.png` (`docs/mkdocs.yml:32-33`) but `docs/assets/` does not exist.
**Fix:** Correct the nav paths to `tutorials/basic-workflow.md`, `tutorials/large-genomes.md`, `tutorials/integration.md`, and `user-guide/performance-tips.md`; either add the `docs/assets/` files or remove the `logo`/`favicon` keys; run `cd docs && mkdocs build --strict` before committing.

### WR-05: docs site footer PyPI link is a 404

**File:** `docs/mkdocs.yml:123`
**Issue:** The social link points to `https://pypi.org/project/rustkmer`, which returns 404 (verified live). The published project is `pyrustkmer` (`https://pypi.org/pypi/pyrustkmer/json` resolves and is authored by "RustKmer Team"); every doc that says `pip install pyrustkmer` is correct, making this link inconsistent with the rest of the corpus.
**Fix:** `link: https://pypi.org/project/pyrustkmer/`.

### WR-06: "Verify Installation" snippet is a Python syntax error

**File:** `docs/installation.md:32`, `docs/index.md:56`
**Issue:** Both files' installation-verification step contains a misplaced parenthesis inside an f-string:

```python
print(f"Total k-mers: {counter.get_stats().total_kmers)}")
```

`total_kmers)}` closes the expression at `)` and leaves a stray `}` — `SyntaxError: f-string: matching '}' not found` on copy-paste. The very first code a new Python user is told to run fails.
**Fix:** `print(f"Total k-mers: {counter.get_stats().total_kmers}")` in both files.

### WR-07: Migration table documents CLI commands the CLI rejects

**File:** `docs/api-reference/index.md:228-229` (same defects at `docs/api-reference/overview.md:382`)
**Issue:** Two of the "From Rust CLI to Python API" rows show invalid CLI invocations:

- `rustkmer dump db.rkdb --limit 1000` — the `Dump` subcommand takes only a positional `<DATABASE>` and `-o/--output` (`src/cli/args.rs:141-149`); there is no `--limit`. `docs/examples/data-export.md:34` explicitly documents "`-o` is the only option `dump` takes — there is no `--limit` or `--format` flag", so the two docs contradict each other and the code.
- `rustkmer merge a.rkdb b.rkdb -o merged.rkdb` — `Merge` has no positional inputs; it requires `-i/--input` with `num_args = 2..` (`src/cli/args.rs:249`).

The Python-side equivalents on those rows are valid (`PyDatabase.dump(limit=...)` and the `PyDatabase.merge` staticmethod exist with those signatures), so only the CLI column needs fixing.
**Fix:** `rustkmer dump db.rkdb` (drop the limit, note pagination is Python-only) and `rustkmer merge -i a.rkdb b.rkdb -o merged.rkdb`.

### WR-08: Example scripts point users at guide documents that do not exist

**File:** `examples/python/demo_pyo3_binding.py:283-286`, `examples/python/test_pyo3_api.py:225`
**Issue:** Both scripts print "further reading" pointers to `PYO3_PYTHON_BINDING_GUIDE.md` and `PREFIX_QUERY_USAGE_GUIDE.md`. Neither file exists anywhere in the repository (verified by `find` over the whole tree). Commit 2e0efcb ("correct stale cross-references and dead CLI subcommand in demo_pyo3_binding.py") fixed the dead subcommand but left these dangling references; the intended targets exist at `docs/guides/pyo3-binding-guide.md` and `docs/guides/prefix-query-guide.md`.
**Fix:** Update both scripts to reference `docs/guides/pyo3-binding-guide.md`, `docs/guides/prefix-query-guide.md` (and `README.md` for the project overview line).

### Info

### IN-01: docs/mkdocs.yml declares the `search` plugin twice; most of the docs tree is absent from nav

**File:** `docs/mkdocs.yml:52-57`, `docs/mkdocs.yml:82-114`
**Issue:** The `plugins:` list contains two identical `search` entries. Separately, the nav omits `getting-started/`, `troubleshooting/`, `api-reference/python/`, `api-reference/rust/`, `implementation/`, and most of `guides/` and `user-guide/` — dozens of pages the docs effort just wrote are unreachable from the site navigation.
**Fix:** Keep one `search` entry; extend the nav (or use `not_in_nav` deliberately) so the regenerated pages are reachable.

### IN-02: docs/README.md example treats a PyQueryResult as always-truthy

**File:** `docs/README.md:133-135`
**Issue:** `if result:` — `PyQueryResult` is a `#[pyclass]` with no `__bool__`, so a pyclass instance is always truthy; a not-found query still prints "找到: 0". Misleading pattern for users copying the example.
**Fix:** `if result.found:`.

### IN-03: demo_performance.py — misleading unit name and inconsistent zero-guard

**File:** `examples/python/demo_performance.py:121-125`
**Issue:** `throughput_mbps` holds GB/s (printed as "GB/s") — the name says Mb/s. Its sibling `queries_per_second = len(query_times) / sum(query_times)` lacks the `if avg_load_time > 0 else 0` guard used two lines above; if every timed query rounded to exactly 0.0 s (possible on a tiny database with a coarse timer) the script would crash with ZeroDivisionError instead of printing the summary.
**Fix:** Rename to `throughput_gbps`; guard with `sum(query_times) or 1.0` (or mirror the conditional-expression form).

### IN-04: Inconsistent GitHub org across the doc corpus

**File:** `docs/installation.md:212`, `docs/mkdocs.yml:3-4` vs `CONTRIBUTING.md:13`, `docs/mkdocs.yml:121`, `docs/installation.md:100`
**Issue:** Some references point at `github.com/rustkmer/rustkmer` (issues link, mkdocs `repo_url`), others at `github.com/zhangtaolab/rustkmer` (CONTRIBUTING clone URL, mkdocs social link, docs/installation clone URL). At most one org is real; issue links in the wrong repo dead-end.
**Fix:** Pick the canonical repository URL and use it everywhere (`repo_url`, `edit_uri` implications included).

### IN-05: mkdocs preview server binds all interfaces

**File:** `docs/mkdocs.yml:146`
**Issue:** `dev_addr: 0.0.0.0:8000` exposes the local docs preview on every network interface; the common default is `127.0.0.1:8000`.
**Fix:** `dev_addr: 127.0.0.1:8000` unless remote preview is intentional.

### IN-06: Uninterpolated `{route}` placeholders in expect_err messages

**File:** `tests/merge_bounded_memory_tests.rs:670`, `tests/merge_bounded_memory_tests.rs:679`
**Issue:** `.expect_err("{route}: the streaming route must fail on a nonexistent temp_dir")` and the prefix-cache analogue pass a literal `{route}` — `expect_err` takes a plain message, so a panic there prints the raw placeholder instead of which route failed. Cosmetic: the assertions that follow identify the route.
**Fix:** `expect_err(&format!("{route:?}: the streaming route must fail ..."))` or drop the placeholder.

---

_Reviewed: 2026-10-20T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
