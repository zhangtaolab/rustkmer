---
phase: 09-python-parity
reviewed: 2026-11-13T02:33:28Z
depth: standard
files_reviewed: 18
files_reviewed_list:
  - pyo3/src/counter.rs
  - pyo3/src/lib.rs
  - src/database/format.rs
  - pyo3/tests/test_counter.py
  - pyo3/tests/test_version.py
  - pyo3/tests/test_public_api.py
  - pyo3/tests/test_counter_concurrency.py
  - pyo3/tests/test_save_database_byte_identity.py
  - tests/sorted_pairs_constructor_tests.rs
  - scripts/bench/python_bench.py
  - scripts/bench/tests/test_python_bench.py
  - scripts/bench/n_read_differential.py
  - scripts/bench/tests/test_n_read_differential.py
  - scripts/bench/README.md
  - docs/user-guide/n-read-semantics.md
  - docs/user-guide/index.md
  - mkdocs.yml
  - pyo3/README.md
findings:
  critical: 0
  warning: 4
  info: 8
  total: 12
  necessity: 0
status: issues_found
---

# Phase 9: Code Review Report

**Reviewed:** 2026-11-13T02:33:28Z
**Depth:** standard
**Files Reviewed:** 18
**Status:** issues_found

## Summary

The Rust/PyO3 core of this phase is sound. Every `py.detach` closure captures only owned `Send` values (`String` path, cloned `Arc<RustPyCounter>`, `SequenceKind`, `usize`) and all three are `move`; no deprecated `allow_threads`, no `unwrap`/`expect` or saturating/wrapping arithmetic on a Python-reachable path, and no new summation site (the merge reuses `KmerCounter::merge_local_counts`'s checked additions). `src/database/format.rs` is a verified pure addition (`git diff --numstat` = `78 0`, pre-blob `eb0d5bf2…`, post-blob `dedfd95a…`), the new constructor has a caller-order contract plus a debug-only assertion, and its header literal matches `from_kmer_pairs` exactly. The four `save_database` error strings are preserved verbatim, including the empty-counter message.

I independently re-ran the relevant suites on the current tree: `cargo test --test sorted_pairs_constructor_tests` (5 passed), `pytest pyo3/tests/test_counter.py` (119 passed), the three new PyO3 test files (9 passed), `test_save_database_byte_identity.py` (8 passed, cross-surface sha `a5da813e…` reproduced), both bench unit suites (65 passed/1 skip, 33 passed), and a full `n_read_differential.py --expect-unified --previous …` run (exit 0, 9/9 cases equal, `python_only_total` after = 0, `before` sha `6d929a45…` with `python_only_total` = 33). Evidence hashes, pinned blobs, the fixture manifest (`f010e42a…`), the extension version (`0.5.0`), and every number in the new docs all match the committed artifacts.

No Critical findings: I found no incorrect count, byte divergence, GIL-bound capture, injection path, or data-loss risk in the changed Rust/PyO3 code. The findings below are harness-honesty, test-wiring, and documentation gaps. The most material is WR-01: the comparison harness can consume a regenerated baseline whose "t1" arm was not measured at one thread, while the README claims that cannot happen.

## Findings Overview

| ID | Severity | File(s) | Finding | Status |
|----|----------|---------|---------|--------|
| WR-01 | Warning | `scripts/bench/python_bench.py`, `scripts/bench/README.md` | `--emit-baseline` can label a non-1-thread arm as `-t1`; compare mode selects `arms[0]` positionally and never checks its thread configuration | Fixed — `72a8399` |
| WR-02 | Warning | `scripts/bench/python_bench.py` | Compare mode silently ignores `--threads` and never observes the worker's actual thread configuration | Fixed — `266492a` |
| WR-03 | Warning | `pyo3/tests/test_save_database_byte_identity.py`, `.github/workflows/{ci,benchmark}.yml` | The cross-surface byte-identity suite skips in every CI job, including the fixture-only Python arm | Fixed — `669e91f` |
| WR-04 | Warning | `mkdocs.yml`, `mkdocs.docs.yml`, `docs/user-guide/index.md` | The N-read semantics page is absent from the deployed docs config's nav; the strict docs build was never run | Fixed — `af4d954` |
| IN-01 | Info | `pyo3/tests/test_save_database_byte_identity.py`, `pyo3/tests/test_counter_concurrency.py` | These preservation gates also pass on the parent implementation; they do not prove the single-sort/GIL-release change | Open — out of fix scope |
| IN-02 | Info | `pyo3/tests/test_counter.py` | Stale docstring still describes the retired `LocalKmerCounts` file path | Open — out of fix scope |
| IN-03 | Info | `pyo3/src/counter.rs` | `save_database`'s non-linearizable snapshot under concurrent mutation is undocumented | Open — out of fix scope |
| IN-04 | Info | `scripts/bench/n_read_differential.py` | `--previous` accepts any structurally valid differential as the "before" state; no prior-state/sha guard | Open — out of fix scope |
| IN-05 | Info | `scripts/bench/n_read_differential.py`, `docs/user-guide/n-read-semantics.md` | The `record_boundary` case cannot detect cross-record joins under skip-N | Open — out of fix scope |
| IN-06 | Info | `scripts/bench/tests/test_n_read_differential.py` | `test_missing_extension_exits_2` fails when the extension is importable (demonstrated under `.venv313`) | Open — out of fix scope |
| IN-07 | Info | `pyo3/src/counter.rs` | `SaveDatabaseError::Database` is an unreachable error arm | Open — out of fix scope |
| IN-08 | Info | `scripts/bench/python_bench.py`, `scripts/bench/bench.py` | Compare mode accepts `--reps 1` and ignores CV warnings, so a single noisy sample can PASS | Open — out of fix scope |

## Critical Issues

None.

## Warnings

### WR-01: Baseline capture can label a non-1-thread arm as the t1 comparison basis

**Status:** Fixed in `72a8399`. `--emit-baseline` now requires `--threads 1`; arm names derive from the configuration actually measured (`threads_suffix`); baseline selection is by identity (single arm named `*-n-free-control-t1` with `threads == 1`) in `validate_baseline_identity`, `compare_to_baseline`, and `build_baseline`, never `arms[0]`. Guarded by `test_baseline_arm_selected_by_identity_not_position`, `test_t1_named_arm_measured_at_default_threads_raises`, `test_emit_baseline_requires_one_thread`, and the new identity/build-baseline guard tests.

**File:** `scripts/bench/python_bench.py:788`, `scripts/bench/python_bench.py:858`, `scripts/bench/python_bench.py:332-353`, `scripts/bench/python_bench.py:375-426`, `scripts/bench/README.md:192-196`

**Issue:** In non-compare slice mode the control arm is always named `py{k}-n-free-control-t1` (line 788) but is measured with `threads_text=args.threads` (line 858). Nothing rejects `--emit-baseline --threads default` (or `--threads 4`), so a baseline can be emitted whose `n_free_control.arms[0]` is named `-t1` while its `threads` field records `"default"`/`4`. `compare_to_baseline` then takes `baseline["n_free_control"]["arms"][0]` positionally as `baseline_t1` (line 346), and `validate_baseline_identity` never inspects the arm's name or thread configuration. A regenerated baseline can therefore silently supply an all-cores median to `speedup_t1` and `speedup_default`. This contradicts the README's claim that "a synthetic or mislabeled baseline cannot be committed as a real one" (lines 192-196). The committed baseline is correct (`platform: darwin`, `arms[0].threads == 1`, median 32.14), so the delivered 2.3006x/8.4802x evidence is unaffected — but the guard is not what the documentation says.

**Fix:** Force baseline capture to one thread: reject `--emit-baseline` unless `args.threads == "1"`, or derive the control arm's name from the actual `threads_text`. Independently, make `validate_baseline_identity`/`compare_to_baseline` require exactly one control arm with `threads == 1` (and a `-t1` name) and fail exit 2 otherwise:

```python
matches = [a for a in arms
           if str(a.get("name", "")).endswith("-n-free-control-t1")
           and a.get("threads") == 1]
if len(matches) != 1:
    raise ValueError("baseline has no unambiguous threads=1 control arm")
```

### WR-02: Compare mode ignores `--threads` and never observes the measured thread configuration

**Status:** Fixed in `266492a`. Compare mode rejects any `--threads` other than `1` (exit 2, no artifact); the worker reports the binding's own resolved rayon count via `get_stats().threads` (new read-only `PyCounterStats.threads`, leaving `PyCounter`'s frozen twelve-name surface untouched); `validate_worker_stats` requires `threads_resolved` to match the arm's requested configuration and `check_rep_identity` pins it across reps. A `PyCounter` that ignores `threads` can no longer produce a PASS. Guarded by `test_binding_ignoring_threads_exits_2`, `test_resolved_threads_mismatch_raises`, `test_thread_resolution_disagreement_raises`, and `test_compare_rejects_non_default_threads`.

**File:** `scripts/bench/python_bench.py:721`, `scripts/bench/python_bench.py:833-842`, `scripts/bench/python_bench.py:885-886`, `scripts/bench/python_bench.py:586`, `scripts/bench/python_bench.py:222-254`

**Issue:** In compare mode `--threads` is parsed and validated (line 721) and then discarded: the arms are hard-coded `"1"` and `"default"` (lines 836, 841) and `params.threads` is forced to `1` (lines 885-886). A user passing `--threads 4 --compare-baseline` gets a silent no-op — the exact class of defect PAR-01 fixed for the CLI. More importantly, the worker writes `"threads": args.threads` into its stats payload (line 586), but `validate_worker_stats` never reads that field, and the arm's `threads` value in the artifact is derived from the requested string (lines 646-652), not an observation. If `PyCounter` ever regressed to ignoring its `threads` argument, both arms would run with the global rayon pool's first-call configuration and the comparison would still produce a PASS. The current evidence's 13.97 s vs 3.79 s ratio corroborates real parallelism, so this is a hardening gap rather than a refutation of the measured numbers.

**Fix:** Reject a non-default `--threads` when `--compare-baseline` is set (and document that compare mode always measures `t1` and `default`). Additionally, record an observed signal per rep — e.g., a `PYRUSTKMER_THREADS_DIAGNOSTICS`-gated attribute or an env-var-gated report of the engine's worker count — and require it to match the arm's requested configuration before the verdict is computed.

### WR-03: The cross-surface byte-identity suite skips in every CI job

**Status:** Fixed in `669e91f`. The skip guards are split: `_require_fixture()` for the fixture-only Python golden arm, `_require_cli()` (plus the fixture) for the CLI and 1-vs-N arms. Verified in the exact CI shape with no release binary: 6 passed, 4 skipped (only the CLI arms skip). Guarded by `test_fixture_only_arm_does_not_require_the_cli` and `test_cli_guard_skips_gracefully_when_the_binary_is_absent`.

**File:** `pyo3/tests/test_save_database_byte_identity.py:90-95`, `pyo3/tests/test_save_database_byte_identity.py:127-143`, `.github/workflows/ci.yml:134-184`, `.github/workflows/benchmark.yml:87-121`

**Issue:** `_require_build_artifacts()` skips unless both `target/release/rustkmer` and the committed fixture exist. The `pyo3-pytest` CI job builds only the maturin wheel (`ci.yml:175-176`) and never builds the root CLI; the benchmark workflow builds the CLI (`benchmark.yml:87-90`) but never runs pytest. Consequently 6 of the 8 tests in this file skip in CI — including `test_python_save_database_matches_golden`, which needs only the committed fixture and the installed extension. A future regression in `save_database`'s emitted bytes would not turn CI red. The phase's evidence is still valid (09-05 ran the suite locally with the release binary: 8 passed, reproduced here), but the standing gate does not exist.

**Fix:** Split the skip guards — a fixture-only guard for the Python-vs-committed-golden arm and a CLI guard for the CLI and 1-vs-N arms — and either add `cargo build --release --locked` to the `pyo3-pytest` job or add a dedicated CI step that runs this file after the release build.

### WR-04: The N-read semantics page is absent from the deployed docs nav

**Status:** Fixed in `af4d954`. `mkdocs.docs.yml` — the config the Documentation workflow actually builds (`mkdocs build -f mkdocs.docs.yml --strict`, `gh-deploy -f mkdocs.docs.yml`) — now lists `user-guide/index.md` and `user-guide/n-read-semantics.md` under User Guide. The root `mkdocs.yml` entry is retained. Verified by grep; `mkdocs build --strict` is not runnable on this host (`section-index` plugin absent), as directed.

**File:** `mkdocs.yml:53`, `mkdocs.docs.yml:77-104`, `.github/workflows/docs.yml:67`, `.github/workflows/docs.yml:87`, `.github/workflows/docs.yml:149`, `docs/user-guide/index.md:8`

**Issue:** The page was added to the root `mkdocs.yml` nav (line 53) and linked from `docs/user-guide/index.md` (line 8), but the Documentation workflow builds and deploys with `mkdocs build -f mkdocs.docs.yml` (also `gh-deploy -f mkdocs.docs.yml`), and that config's nav does not list `user-guide/n-read-semantics.md` — nor `user-guide/index.md`, so the new link is not reachable from any nav entry on the published site. Root `mkdocs.yml` appears in the workflow's trigger paths but is never built. The phase skipped `mkdocs build --strict` (09-04), so this wiring was never exercised. The page is still built as an unlisted page and `pyo3/README.md` carries the migration note, but the ratified behavior change is not navigable on the documentation site.

**Fix:** Add `N-read Semantics: user-guide/n-read-semantics.md` under the User Guide section of `mkdocs.docs.yml` (or confirm root `mkdocs.yml` is the intended deployed config and update the workflow), then run `mkdocs build -f mkdocs.docs.yml --strict` as the gate.

## Info

### IN-01: Preservation gates also pass on the parent implementation

**File:** `pyo3/tests/test_save_database_byte_identity.py`, `pyo3/tests/test_counter_concurrency.py`

**Issue:** Both suites are useful regression gates, but neither distinguishes this phase's change. The parent `save_database` also emitted these exact bytes (stable sort + `from_kmer_pairs(.., sorted: true)`), and the parent file methods already merged per-call `LocalKmerCounts` through the concurrent-safe `merge_local_counts`. The new properties (single `par_sort_unstable_by_key`, `from_sorted_kmer_pairs`, GIL release) are proven by code inspection and the 09-02 static greps, not by a test. The file docstring is honest that it is a preservation test.

**Fix:** No code change required; keep these as preservation gates and avoid citing them as proof that the double sort was removed. If test-level proof is desired, add a test-only allocation/sort counter or a debug-build hook around the save path.

### IN-02: Stale test docstring describes the retired `LocalKmerCounts` file path

**File:** `pyo3/tests/test_counter.py:1116-1126` (line 1121)

**Issue:** "The file helpers now create one `LocalKmerCounts` per file call and merge it once at the end" is no longer true: `add_from_fasta`/`add_from_fastq` build a per-call `CountEngine` and call `CountResult::merge_into`. A reader debugging a parity failure would be pointed at the wrong layer.

**Fix:** Update the docstring to say the file helpers count through a per-call `CountEngine` and merge its partition tables via the checked `merge_local_counts` bridge; `add_sequence` stays on the shared increment path.

### IN-03: `save_database`'s non-linearizable snapshot is undocumented

**File:** `pyo3/src/counter.rs:444-459`, `pyo3/src/counter.rs:703-712`, `pyo3/src/counter.rs:724-727`

**Issue:** `save_database_on_counter` snapshots with `counter.get_all_counts()` outside any lock. `PyCounter` is `Sync`, so another Python thread can call `add_*` or `reset` concurrently; the result is a valid database that is not necessarily any point-in-time state. The phase decision explicitly accepts a non-linearizable snapshot, but neither the method docstring nor the helper doc says so, and the docstring instead claims the bytes are "identical to the CLI count output" — a claim with no defined meaning under concurrent mutation.

**Fix:** Add one sentence to the `save_database` docstring: the counter is snapshotted without locking, so a concurrent `add_*`/`reset` may or may not be reflected; the emitted file is always internally consistent.

### IN-04: `--previous` accepts any structurally valid differential as the "before" state

**File:** `scripts/bench/n_read_differential.py:144-194`, `scripts/bench/n_read_differential.py:327-349`

**Issue:** `load_previous` validates `k`, `canonical`, the case-name set, and each case's count shape, but copies `expectation` and `totals` through unvalidated and never pins the committed Phase 5 sha256. A post-D2 or arbitrary differential with the right case set is accepted and embedded as `before`, so a re-run could publish an artifact whose "before" block shows zero divergence while still exiting 0. The delivered artifact is correct (`before.sha256 = 6d929a45…`, `python_only_total = 33`, verified), so this is defense-in-depth.

**Fix:** Require `data.get("expectation") == "divergence"` and a positive integer `totals.python_only_total`, and either validate the totals shape or accept only the committed artifact's sha256 (`6d929a45…`).

### IN-05: The `record_boundary` case cannot detect cross-record joins under skip-N

**File:** `scripts/bench/n_read_differential.py:96-102`, `docs/user-guide/n-read-semantics.md:15-17`

**Issue:** The `build_cases` docstring says terminal Ns mean "equality here proves there are no cross-record joins". Post-D2 that reasoning no longer holds: if an implementation concatenated records before extracting windows, the boundary-spanning windows would contain the terminal N on each side and be skipped under skip-N, so the counts would be identical either way. The docs' "windows never span record boundaries" claim is true by code inspection (`count_sequence(record.seq())` per record) and is covered by the multi-record N-free Python unit tests, but not by this differential case.

**Fix:** Add a two-read N-free case (or extend the fixture with an N-free multi-record case) whose concatenation would create chimeric windows, and soften the docstring to say the case covers the pre-D2 strip-and-join form.

### IN-06: `test_missing_extension_exits_2` fails when the extension is importable

**File:** `scripts/bench/tests/test_n_read_differential.py:259-269`

**Issue:** The test uses `--rustkmer sys.executable` as a stand-in for an interpreter without `pyrustkmer`. When the suite is run under `.venv313/bin/python` (where the extension is installed), the import succeeds, the run proceeds to invoke `python count ...`, and the test fails with `'pyrustkmer' not found in "... CLI count failed ..."`. Reproduced locally: FAIL under `.venv313/bin/python`, passes under system `python3` (the documented invocation, `benchmark.yml:87-90`). The test predates Phase 9, but this phase moved the shared `run_main` helper and left the fragility in place.

**Fix:** Skip the test when `pyrustkmer` imports in the test interpreter, or use a guaranteed-extension-free interpreter and assert only on `rc == 2` plus the specific "cannot import pyrustkmer" message.

### IN-07: `SaveDatabaseError::Database` is an unreachable error arm

**File:** `pyo3/src/counter.rs:685`, `pyo3/src/counter.rs:733-738`

**Issue:** `RKDatabase::from_sorted_kmer_pairs` never returns `Err` (it builds a header and maps entries), so the `map_err(|e| SaveDatabaseError::Database(...))` arm and its "Failed to create database: …" message can never execute. Harmless, but it is error plumbing that exists only because the constructor's signature returns `ProcessingResult`.

**Fix:** Keep it if the constructor is expected to gain validation; otherwise document the arm as defensive or make the constructor return `Self`.

### IN-08: Compare mode accepts a single rep and ignores CV warnings

**File:** `scripts/bench/python_bench.py:717-718`, `scripts/bench/python_bench.py:923-924`, `scripts/bench/bench.py:1203-1224`, `scripts/bench/README.md:212`

**Issue:** `--reps` is validated only as `>= 1`, so `--compare-baseline --reps 1` runs one measured sample per arm (`reduce_arm` then records `cv_wall_pct: null`). The verdict is computed from the median regardless of `cv_warning`; `reduce_arm` deliberately treats high CV as a warning, not an error. The README states "There is no noise band", so a one-sample or high-variance run can clear 1.2x by noise and still exit 0. The artifact records `reps` and CV (the delivered run used 3 reps at 1.0% / 0.46% CV), so it is auditable, but the gate itself does not enforce measurement quality.

**Fix:** Require `--reps >= 3` in compare mode, and either exit 2 or record and require a `measurement_quality: PASS` field when either arm's `cv_warning` is true.

---

_Reviewed: 2026-11-13T02:33:28Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
