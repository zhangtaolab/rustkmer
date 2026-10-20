---
phase: quick-261018-ret
plan: 01
type: execute
subsystem: examples
tags: [examples, python, pyrustkmer, fixtures]
requires: []
provides: [runnable-examples-python-suite]
affects: [examples/python]
key-files:
  modified:
    - examples/python/test_pyo3_api.py
    - examples/python/unified_query_example.py
    - examples/python/simple_prefix_query.py
    - examples/python/demo_fuzzy.py
    - examples/python/demo_fuzzy_enhanced.py
    - examples/python/demo_performance.py
    - examples/python/demo_position_mutations_fixed.py
    - examples/python/demo_pyo3_binding.py
decisions:
  - "Demo patterns derive from the loaded database's kmer_size at runtime instead of hardcoded 19-mer literals, so any k fixture (or user db via argv/env) produces real-length queries"
  - "unified_query_example.py's fuzzy demo routes through PyFuzzyQuery (real engine) because PyDatabase.query_fuzzy is a Rust-side placeholder that always returns 0 matches"
  - "demo_pyo3_binding.py builds its temp database with the current `count -i -o -k` CLI (build-kmer-db subcommand no longer exists) and resolves the binary from the repo root"
requirements-completed: ["QUICK-261018-EXAMPLES"]
duration: 12 min
completed: 2026-10-18T12:03:00Z
status: complete
actuals:
  tokens: 7500 # chars/4 over the realized examples/python diff (30009 chars)
  tasks: 3
  commits: 3 # MEASURED: git rev-list --count 6381229..HEAD
plan_head_before: 6381229a0891fcc1544c65f77305642710fe9341
plan_head_after: 2e0efcbd6d4be4798e4f346ea48bf7b0be72ef0c
---

# Quick Task 261018-ret: Fix examples/python legacy-API scripts Summary

Repaired all 9 scripts in examples/python/ to run against the current pyrustkmer module using repo-local k=7 fixtures: fixed one SyntaxError, re-pointed 7 scripts away from the author's personal 17.3 GB database to test_data/databases/small_test.rkdb (argv/env override preserved), and replaced hardcoded 19-mer patterns with kmer_size-derived ones so queries return real matches.

## What Was Done

### Task 1: Three outright-broken scripts (commit 79e1dec)
- **test_pyo3_api.py** — matched the three example-code string delimiters (each opened `'''` but closed `"""`, surfacing as SyntaxError at line 165); the usage hint now points at `test_data/databases/small_test.rkdb` instead of `~/Data/.../R1_001.rkdb`.
- **unified_query_example.py** — fixture dir changed from the nonexistent `python/tests/test_data` to `test_data/databases` (tiny-first selection order kept per plan); exact probes (`"A"*k` etc.), prefixes (sliced from k-length probes), hybrid patterns (`"A{N%d}C" % (k-2)` etc.), and fuzzy patterns all derive from `db.kmer_size`; the ~60-line k==7 pattern-comment graveyard in demo_hybrid_query was replaced by 4 generically derived patterns; fuzzy demo routed through `PyFuzzyQuery` (see Deviations).
- **simple_prefix_query.py** — default path resolves repo-relative `test_data/databases/small_test.rkdb` via `Path(__file__).resolve().parents[2]`; optional `argv[1]` (db) / `argv[2]` (pattern) override; hybrid/prefix/batch patterns derive from the loaded k.

### Task 2: demo_fuzzy-family re-pointed to fixtures (commit 38af69e)
- All four demos (demo_fuzzy, demo_fuzzy_enhanced, demo_performance, demo_position_mutations_fixed) resolve `db_path` as `argv[1] > $RUSTKMER_EXAMPLE_DB > repo fixture`; the false "Loading 17.3GB genomic database..." banner now just says "Loading database...".
- Patterns built from `db.kmer_size`: `"A"*k`, `"T"*k`, N-wildcard probes of total length k; position-mutation groups stay within `[0, k)` and respect the engine's group-limit ≤ position-count rule (see Deviations).
- demo_performance.py: batch patterns built to exactly k chars (the old `len==19` filter emptied the batch and the summary divided by zero); deprecated `fuzzy.fuzzy_query` calls renamed to `query_fuzzy`; throughput computed from the actual file size instead of the hardcoded 17.3 GB.
- demo_position_mutations_fixed.py: the dead try-chain (`fuzzy_query(pattern, _max_mutations, ...)` — wrong private parameter names, every position case errored) replaced with the unified `query_fuzzy` / `query_fuzzy_position` calls.

### Task 3: demo_pyo3_binding.py + full-directory sweep (commit 2e0efcb)
- Printed hints now reference `test_data/databases/small_test.rkdb` and existing scripts (`simple_prefix_query.py`, `unified_query_example.py`); the nonexistent `prefix_query_pyo3_binding.py` reference is gone.
- Rule 1 fix (see Deviations): the script's temp-database builder invoked the removed `build-kmer-db` CLI subcommand, so the demo body silently skipped on every machine; now uses `count -i -o -k 19` with the binary resolved from the repo root; hybrid demo patterns derive from `engine.kmer_size()` (a method on PyPrefixQuery, unlike the property on PyDatabase).

## Verification Results

All commands run from the repo root with `.venv313/bin/python`:

| Check | Result |
|---|---|
| Task 1 gate: ast.parse x3 + run x3 | TASK1-OK |
| Task 2 gate: run x4 + `grep -rc "forrest/Data"` | TASK2-OK (0 hits) |
| Task 3 gate: run all `examples/python/*.py` + stale-ref grep | ALL-SCRIPTS-OK |
| ast.parse over all 9 scripts | OK |
| Every script exits 0, no arguments | 9/9 |
| `grep -rl "forrest/Data\|~/Data\|prefix_query_pyo3_binding" examples/python/` | empty |
| `grep -rl "test_256_prefix" examples/python/` | empty (no legacy-fixture refs) |
| `RUSTKMER_EXAMPLE_DB=medium_test.rkdb demo_fuzzy.py` | loads medium_test.rkdb |
| `simple_prefix_query.py large_test.rkdb` (argv override) | 1024 hybrid matches |
| Run from `/tmp` (any-cwd resolution) | demo_fuzzy + unified exit 0, fixture resolves absolutely |
| Real-match evidence | small_test: hybrid A{N5}C=530, fuzzy A*k=33, position-demo 6/6 queries OK; unified on tiny: fuzzy 1/35 matches via real engine |

## Deviations from Plan

**1. [Rule 1 - Bug] unified_query_example.py fuzzy demo switched from `db.query_fuzzy` to `PyFuzzyQuery(db).query_fuzzy`**
- **Found during:** Task 1 pre-edit API probe
- **Issue:** `PyDatabase.query_fuzzy` is a placeholder in the Rust binding (pyo3/src/database.rs:670-677 returns `matches: Vec::new(), total_matches: 0` unconditionally). The demo would always print 0 matches — the same silent no-op this task exists to eliminate.
- **Fix:** Route the demo through `pyrustkmer.PyFuzzyQuery(self.db)` — the call shape the plan itself verified as working. `query_time_ms`/`mutation_tolerance`/`match.distance` attributes all exist on the live result, so no other drift.
- **Files:** examples/python/unified_query_example.py
- **Commit:** 79e1dec

**2. [Rule 1 - Bug] demo_pyo3_binding.py invoked the removed `build-kmer-db` CLI subcommand**
- **Found during:** Task 3 baseline run (plan asserted the script "runs clean today"; it exits 0 only because the failure is swallowed and the demo body skipped)
- **Issue:** `rustkmer build-kmer-db` no longer exists (`error: unrecognized subcommand`), so every query demo was silently skipped.
- **Fix:** Use the current `count -i <fasta> -o <db> -k 19`; resolve the release binary from `Path(__file__).resolve().parents[2]` instead of the author's absolute path; drop the personal `sys.path.insert`; derive hybrid patterns from `engine.kmer_size()`.
- **Files:** examples/python/demo_pyo3_binding.py
- **Commit:** 2e0efcb

**3. [Rule 1 - Bug] demo_position_mutations_fixed.py "Complex Configuration" group limit exceeded its position count**
- **Found during:** Task 2 verification (engine rejects `5-6:3`: "Max mutations (3) cannot exceed number of positions (2)")
- **Fix:** Last group limit lowered to 2 (`{k-2}-{k-1}:2`); all groups now satisfy the engine's validation and 6/6 cases run without error.
- **Files:** examples/python/demo_position_mutations_fixed.py
- **Commit:** 38af69e

**Total deviations:** 3 auto-fixed (all Rule 1 bugs). **Impact:** examples now demonstrate the real API surface; no plan scope was added or cut.

## Known Stubs

| Stub | File | Reason |
|---|---|---|
| `PyDatabase.query_fuzzy` always returns 0 matches (Rust-side placeholder) | pyo3/src/database.rs:670-677 | Pre-existing, out of this task's scope (Rust binding, not examples/). Worked around in unified_query_example.py by using PyFuzzyQuery; the placeholder remains for a future binding task. |

## Threat Flags

None. The only trust boundary (argv/env -> read-only PyDatabase open) was already dispositioned `accept` in the plan's threat model; no new surface was added.

## Self-Check: PASSED

All 8 modified files exist on disk; all 3 task commits (79e1dec, 38af69e, 2e0efcb) are ancestors of HEAD (2e0efcb); SUMMARY.md exists at the required path.
