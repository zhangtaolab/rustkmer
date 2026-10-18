---
phase: quick-261018-ret
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - examples/python/test_pyo3_api.py
  - examples/python/unified_query_example.py
  - examples/python/simple_prefix_query.py
  - examples/python/demo_fuzzy.py
  - examples/python/demo_fuzzy_enhanced.py
  - examples/python/demo_performance.py
  - examples/python/demo_position_mutations_fixed.py
  - examples/python/demo_pyo3_binding.py
autonomous: true
requirements: ["QUICK-261018-EXAMPLES"]
estimate:
  tokens: 30000
  raw_tokens: 20000
  tasks: 3
  confidence: low

must_haves:
  truths:
    - "Every .py script under examples/python/ exits 0 when run as `.venv313/bin/python examples/python/<script>.py` from the repo root with no arguments"
    - "No file under examples/python/ references /Users/forrest/Data or ~/Data; default database paths resolve to repo fixtures under test_data/databases/"
    - "test_pyo3_api.py passes ast.parse (today it dies with SyntaxError at line 165 from mismatched triple-quote delimiters)"
    - "Demo/query patterns are derived from the loaded database's kmer_size (repo fixtures are k=7) instead of hardcoded 19-mer literals"
    - "No script references the legacy-version fixture test_256_prefix.rkdb (readers reject it) or the nonexistent script prefix_query_pyo3_binding.py"
  artifacts:
    - "examples/python/test_pyo3_api.py (parses, runs, hints reference existing scripts/fixtures)"
    - "examples/python/unified_query_example.py (runs against test_data/databases fixtures)"
    - "examples/python/simple_prefix_query.py (defaults to repo fixture, argv override retained)"
    - "examples/python/{demo_fuzzy,demo_fuzzy_enhanced,demo_performance,demo_position_mutations_fixed}.py (fixture-backed)"
    - "examples/python/demo_pyo3_binding.py (stale hints corrected)"
  key_links:
    - "script default DB path -> Path(__file__).resolve().parents[2] / 'test_data' / 'databases' / 'small_test.rkdb' (repo-root-relative, works from any cwd)"
    - "demo query patterns -> lengths built from db.kmer_size so k=7 fixtures produce real matches"
---

<objective>
Make every script in examples/python/ run against the CURRENT pyrustkmer module using repo-local fixtures. Live verification this session found the defect set: test_pyo3_api.py does not even parse (SyntaxError from mismatched triple-quote delimiters); unified_query_example.py dies with FileNotFoundError hunting python/tests/test_data/ (real fixtures live in test_data/databases/); simple_prefix_query.py and the four demo_fuzzy-family scripts hardcode the author's personal 17.3 GB database /Users/forrest/Data/data/kmer/K19/R1_001.rkdb (simple_prefix_query.py exits 1, the demos swallow the failure in a broad except); demo scripts hardcode 19-mer patterns that cannot match the k=7 repo fixtures; demo_pyo3_binding.py's printed hints reference a script that does not exist (prefix_query_pyo3_binding.py) and personal paths.

Purpose: examples/ is the first thing users copy; today 3 of 9 scripts crash outright and 4 more silently no-op on any machine but the author's. The live API already supports everything these scripts call (verified via dir() on the built module: PyDatabase exposes query_exact/query_prefix/query_hybrid/query_fuzzy/fuzzy_query etc.) — the breakage is paths, one syntax error, and pattern lengths, not the API surface.

Output: 8 edited scripts, all runnable via `.venv313/bin/python examples/python/<script>.py` from the repo root.
</objective>

<execution_context>
@~/.claude/gsd-core/workflows/execute-plan.md
@~/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.claude/CLAUDE.md

Verified grounding (this session, do not re-derive):
- Verification env: `.venv313/bin/python` (repo root) has a built pyrustkmer. All commands below assume cwd = repo root.
- Fixtures: test_data/databases/ contains tiny_test.rkdb, small_test.rkdb, medium_test.rkdb, large_test.rkdb, perf_test.rkdb — ALL k=7 (verified: tiny 396 total, small 4318, medium 7986 k-mers). test_256_prefix.rkdb and test_256_prefix_2.rkdb are legacy-version files readers reject — never reference them.
- Live module surface (dir() on built module): PyDatabase -> canonical, database_info, dump, exists, export_all_kmers, export_to_csv, export_to_file, export_to_json, extract_by_pattern, extract_by_prefix, force_lazy_mode, fuzzy_query, get_all_kmers, get_entry_by_index, get_memory_usage, get_stats, is_loaded, kmer_size (PROPERTY, int — not callable), load_mode, merge, parse_pattern, parse_pattern_string, path, query, query_batch, query_exact, query_exact_batch, query_hybrid, query_hybrid_batch, query_prefix, query_prefix_batch, total_kmers, unique_kmers. PyFuzzyQuery -> query_fuzzy, query_fuzzy_position, fuzzy_query, fuzzy_query_with_position_mutations, kmer_size. PyPrefixQuery -> query_prefix_string, query_hybrid, parse_pattern, database_info. PyExtendedPrefixQuery -> query_prefix_metrics, query_hybrid_metrics, query_prefix_batch_metrics, batch_query, query_with_metrics. Result shapes seen working in demo code: PyDatabaseStats{kmer_size, total_kmers, unique_kmers}; PyFuzzyResult{total_matches, matches[]} with match.kmer/match.count; PyQueryResult{kmer, count, found}; PyDatabase(path, load_mode) — load_mode REQUIRED (LoadMode.Preload/MemoryMapped/Lazy).
- Per-file defects (line numbers from current tree):
  - examples/python/test_pyo3_api.py — three example-code dicts open with `'''` (lines 145, 164, 181) but close with `"""` (lines 160, 178, 193); the unterminated string surfaces as SyntaxError at line 165. Line 222 hint embeds a ~/Data personal path.
  - examples/python/unified_query_example.py — lines 299-300 build test_data_dir as parents[2]/"python"/"tests"/"test_data" (nonexistent); real fixtures: parents[2]/"test_data"/"databases". parents[2] depth is already correct (examples/python/x.py -> repo root). Its demo bodies use fixed-length k-mer/prefix/pattern literals that must be derived from db.kmer_size for k=7 fixtures.
  - examples/python/simple_prefix_query.py — line 6 defaults to /Users/forrest/Data/data/kmer/K57/R1_K57_001.rkdb; script takes db path (and pattern) as argv, so keep argv override and change only the default.
  - examples/python/demo_fuzzy.py, demo_fuzzy_enhanced.py, demo_performance.py, demo_position_mutations_fixed.py — line 14 in each: db_path = "/Users/forrest/Data/data/kmer/K19/R1_001.rkdb"; bodies hardcode 19-mer patterns ("AAAAAAAAAAAAAAAAAAA", "GCCCGNNNNNNNNNNNGCC", ...); demo_fuzzy.py's tail `except Exception` prints the error and exits 0 (silent failure). "Loading 17.3GB genomic database..." banner text is now false for fixtures.
  - examples/python/demo_pyo3_binding.py — runs clean today (self-creates a test database) but printed hints at lines ~181-206 reference ~/Data personal paths and the nonexistent script prefix_query_pyo3_binding.py.
- Python style: black line length 88; these are example scripts, keep edits minimal and consistent with each file's existing style. CJK strings in examples/ are acceptable (the Phase-01 CJK rule scoped src/).
</context>

<tasks>

<task type="auto">
  <name>Task 1: Fix the three outright-broken scripts (syntax error, stale fixture dir, personal default path)</name>
  <files>examples/python/test_pyo3_api.py, examples/python/unified_query_example.py, examples/python/simple_prefix_query.py</files>
  <precondition>`.venv313/bin/python -c "import pyrustkmer"` succeeds from the repo root (built extension present). If not, halt and report — do not run maturin yourself in this task.</precondition>
  <action>
  (a) examples/python/test_pyo3_api.py: repair the three example-code string literals so open/close delimiters match (lines 145/160, 164/178, 181/193 — open `'''`, close `"""` today). Pick one delimiter style per block and keep the code text identical. Update the line-222 usage hint to reference the fixture default (`test_data/databases/small_test.rkdb`) instead of ~/Data/data/kmer/K19/R1_001.rkdb. Do not rename or delete any test function.
  (b) examples/python/unified_query_example.py: change the fixture directory from parents[2]/"python"/"tests"/"test_data" to parents[2]/"test_data"/"databases" and keep the first-existing-file selection over [tiny_test.rkdb, small_test.rkdb, medium_test.rkdb, large_test.rkdb]. Then derive every hardcoded k-mer/prefix/pattern literal in the demo methods (demo_exact_query, demo_prefix_query, demo_hybrid_query, demo_fuzzy_query) from the loaded database's kmer_size property (int, not callable) — e.g. "A"*k for exact lookups, k-length prefixes sliced from a generated probe, N-wildcard patterns of total length k — so the demos exercise real queries against k=7 fixtures. Fix any result-attribute drift against the live shapes listed in context (PyQueryResult{kmer, count, found}; PyFuzzyResult{total_matches, matches}; the current code reads result.query_time_ms — verify that attribute exists on the live result object and if absent, time the call with time.time() like the demo_*.py scripts do).
  (c) examples/python/simple_prefix_query.py: replace the personal K57 default at line 6 with a repo-relative resolution of test_data/databases/small_test.rkdb (Path(__file__).resolve().parents[2] / "test_data" / "databases" / "small_test.rkdb"), keeping the existing argv override behavior. If its query patterns are fixed-length and cannot match k=7, derive them from engine.kmer_size the same way.
  </action>
  <verify>
    <automated>.venv313/bin/python -c "import ast; [ast.parse(open(f).read()) for f in ['examples/python/test_pyo3_api.py','examples/python/unified_query_example.py','examples/python/simple_prefix_query.py']]" && .venv313/bin/python examples/python/test_pyo3_api.py >/dev/null && .venv313/bin/python examples/python/unified_query_example.py >/dev/null && .venv313/bin/python examples/python/simple_prefix_query.py >/dev/null && echo TASK1-OK</automated>
  </verify>
  <done>All three scripts parse and exit 0 with no arguments; unified_query_example prints stats from a real fixture database (not the "未找到测试数据库文件" error path); simple_prefix_query needs no arguments to find a database.</done>
</task>

<task type="auto">
  <name>Task 2: Re-point the four demo_fuzzy-family scripts from the personal 17.3 GB database to repo fixtures</name>
  <files>examples/python/demo_fuzzy.py, examples/python/demo_fuzzy_enhanced.py, examples/python/demo_performance.py, examples/python/demo_position_mutations_fixed.py</files>
  <action>
  In all four files: (a) replace line 14's db_path = "/Users/forrest/Data/data/kmer/K19/R1_001.rkdb" with a resolution helper: optional sys.argv[1] override, else env var RUSTKMER_EXAMPLE_DB if set, else Path(__file__).resolve().parents[2] / "test_data" / "databases" / "small_test.rkdb" (add the sys/os/pathlib imports each file needs). (b) Replace hardcoded 19-mer pattern literals with kmer_size-derived ones — after loading the database read db.kmer_size (property) and build patterns like "A"*k, "T"*k, and N-wildcard probes of total length k (e.g. "A"*(k-3) + "NNN") so fuzzy/hybrid queries return real matches on the k=7 fixture. Per-position-mutation structures (demo_position_mutations_fixed.py, demo_fuzzy_enhanced.py) must index within [0, k). (c) Update the "Loading 17.3GB genomic database..." banner to print the actual path (it already prints db_path) without the false size claim. (d) Keep the outer try/except for genuine errors, but after this fix the try body must actually execute — the except branch must not be the path the run takes. Do not restructure the demos beyond these changes; the PyFuzzyQuery(db) + query_fuzzy(pattern, max_mutations=...) call shape already matches the live API (verified working in demo_fuzzy.py's body).
  </action>
  <verify>
    <automated>for f in examples/python/demo_fuzzy.py examples/python/demo_fuzzy_enhanced.py examples/python/demo_performance.py examples/python/demo_position_mutations_fixed.py; do .venv313/bin/python "$f" >/dev/null || exit 1; done && grep -rc "forrest/Data" examples/python/demo_fuzzy.py examples/python/demo_fuzzy_enhanced.py examples/python/demo_performance.py examples/python/demo_position_mutations_fixed.py | grep -v ":0" && exit 1 || exit 0</automated>
  </verify>
  <done>All four demos exit 0, run their try-block against small_test.rkdb, print nonzero-fixture stats (k=7, thousands of k-mers), and no longer contain the personal path anywhere in the file.</done>
</task>

<task type="auto">
  <name>Task 3: Correct stale cross-references in demo_pyo3_binding.py and run the full-directory sweep</name>
  <files>examples/python/demo_pyo3_binding.py</files>
  <action>
  (a) In examples/python/demo_pyo3_binding.py update the printed hint block (~lines 178-210): replace ~/Data/data/kmer/K19/R1_001.rkdb occurrences with test_data/databases/small_test.rkdb (fixture default) and replace the reference to the nonexistent prefix_query_pyo3_binding.py with an existing script (simple_prefix_query.py or unified_query_example.py). This script already runs correctly (it self-creates a test database); change only the hint strings, not the logic. (b) Sweep: run every .py in examples/python/ with .venv313/bin/python and confirm exit 0; confirm zero references remain to personal paths or the nonexistent script across the directory.
  </action>
  <verify>
    <automated>for f in examples/python/*.py; do .venv313/bin/python "$f" >/dev/null || { echo "FAIL $f"; exit 1; }; done && [ "$(grep -rl "forrest/Data\|~/Data\|prefix_query_pyo3_binding" examples/python/ | wc -l | tr -d " ")" = "0" ] && echo ALL-SCRIPTS-OK</automated>
  </verify>
  <done>All 9 scripts in examples/python/ exit 0 from the repo root with no arguments; grep finds no personal path or nonexistent-script reference anywhere under examples/python/.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| argv/env -> PyDatabase path | Scripts accept an optional argv[1] / RUSTKMER_EXAMPLE_DB database path passed to PyDatabase (read-only open of a .rkdb file) |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-quick261018ret-01 | Information Disclosure | example scripts' argv path handling | low | accept | Local example scripts opening a user-specified read-only .rkdb; same trust level as the CLI query command; no network or write surface added |
</threat_model>

<verification>
- `.venv313/bin/python -c "import ast; ..."` over all 9 scripts passes (syntax gate).
- Every script in examples/python/ exits 0 via `.venv313/bin/python examples/python/<script>.py` from the repo root, no arguments.
- `grep -rl "forrest/Data\|~/Data\|prefix_query_pyo3_binding" examples/python/` returns nothing.
- Unified/demo scripts print real fixture stats (k=7) rather than falling into their error/except branches.
</verification>

<success_criteria>
- The 5 companion scripts named by the docs audit (test_pyo3_api.py, unified_query_example.py, simple_prefix_query.py, and the demo family) plus the two remaining same-defect demos all run against the current module with repo fixtures — verified by actually running them, not by inspection.
- Default database resolution is repo-root-relative (works from any cwd) with argv/env override preserved where it already existed.
- No fixture pinned to the legacy-version files (test_256_prefix*.rkdb).
</success_criteria>

<output>
Create `.planning/quick/261018-ret-fix-examples-python-legacy-api-scripts/261018-ret-SUMMARY.md` when done
</output>
