---
phase: 09-python-parity
verified: 2026-11-13T03:16:01Z
status: passed
score: 38/38 must-haves verified
covered_files:
  - ".planning/phases/09-python-parity/09-01-PLAN.md"
  - ".planning/phases/09-python-parity/09-01-SUMMARY.md"
  - ".planning/phases/09-python-parity/09-02-PLAN.md"
  - ".planning/phases/09-python-parity/09-02-SUMMARY.md"
  - ".planning/phases/09-python-parity/09-03-PLAN.md"
  - ".planning/phases/09-python-parity/09-03-SUMMARY.md"
  - ".planning/phases/09-python-parity/09-04-PLAN.md"
  - ".planning/phases/09-python-parity/09-04-SUMMARY.md"
  - ".planning/phases/09-python-parity/09-05-PLAN.md"
  - ".planning/phases/09-python-parity/09-05-SUMMARY.md"
  - "docs/user-guide/index.md"
  - "docs/user-guide/n-read-semantics.md"
  - "mkdocs.docs.yml"
  - "mkdocs.yml"
  - "pyo3/README.md"
  - "pyo3/src/counter.rs"
  - "pyo3/src/lib.rs"
  - "pyo3/tests/test_counter.py"
  - "pyo3/tests/test_counter_concurrency.py"
  - "pyo3/tests/test_public_api.py"
  - "pyo3/tests/test_save_database_byte_identity.py"
  - "pyo3/tests/test_version.py"
  - "scripts/bench/README.md"
  - "scripts/bench/n_read_differential.py"
  - "scripts/bench/python_bench.py"
  - "scripts/bench/tests/test_n_read_differential.py"
  - "scripts/bench/tests/test_python_bench.py"
  - "src/database/format.rs"
  - "tests/sorted_pairs_constructor_tests.rs"
covered_digest: "v4:sha256:c469e1d9782dc289f344fc3580dfaecd06904462ca92c9e8ce70cf82fd9be1d9"
behavior_unverified: 0
overrides_applied: 0
decision_coverage:
  honored: 0
  total: 0
  not_honored: []
---

# Phase 9: Python Parity Verification Report

**Phase Goal:** Python users get the same engine speed and counting semantics as the CLI — proven by measurement against the Phase 5 baseline — with the public API frozen and the N-read output change explicitly documented.
**Verified:** 2026-11-13T03:16:01Z
**Status:** passed
**Re-verification:** No — initial verification (no prior `09-VERIFICATION.md` in the phase directory)

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `PyCounter.add_from_fastq` / `add_from_fasta` count through the shared engine (no sequential line loop) | ✓ VERIFIED | `pyo3/src/counter.rs:676-687` — exactly one `CountEngine::new`, one `count_file(`, one `finish()?.merge_into`; zero `reader.lines()` in the file |
| 2 | The public `PyCounter` API is unchanged (exactly the 12 frozen names) | ✓ VERIFIED | `dir(pyrustkmer.PyCounter)` = 12 names, independently enumerated; `pyo3/tests/test_public_api.py` set-equality test passed |
| 3 | The `save_database` double-sort is gone | ✓ VERIFIED | `pyo3/src/counter.rs:747` single `par_sort_unstable_by_key`; `:749` `from_sorted_kmer_pairs`; zero stable `.sort_by_key(` and zero `from_kmer_pairs` in `counter.rs`; `format.rs:715-751` constructor performs no sort |
| 4 | Every parallel/blocking PyO3 path uses `py.detach` with owned `Send` captures | ✓ VERIFIED | Three `py.detach(move ...)` sites (`counter.rs:399`, `:452`, `:505`) capturing `String`, cloned `Arc`, `usize`, `SequenceKind`; zero `allow_threads` anywhere in `src/` or `pyo3/src/` |
| 5 | The extension is rebuilt and version-asserted before pytest | ✓ VERIFIED | Gates run `maturin develop --release` → no-skip `__version__` assert (`0.5.0`) → pytest, in that order; observed `.so` sha256 `6d526431…` equals the evidence's `provenance.module.sha256`; `test_version.py` has no skip guard and passed |
| 6 | N-read differential shows the chimeric-k-mer divergence eliminated | ✓ VERIFIED | `evidence/n_read_differential_d2.json`: `verdict.result=PASS`, `divergent_cases=[]`, `python_only/cli_only/count_delta` totals `0/0/0`; independently re-run → PASS, divergent=0 |
| 7 | The N-read output change is documented — never silent | ✓ VERIFIED | `docs/user-guide/n-read-semantics.md` (115 lines) + root `mkdocs.yml` nav + deployed `mkdocs.docs.yml` nav + `docs/user-guide/index.md:8` link + `pyo3/README.md:309` migration subsection + method docstrings; exact numbers verified below |
| 8 | The Python benchmark shows a measured wall-clock win vs the committed Phase 5 baseline | ✓ VERIFIED | Evidence `speedup_t1=2.3511` (≥1.0), `speedup_default=8.7100` (≥1.2), `result=PASS`; independent re-run `2.2682` / `8.5479`, `PASS`, exit 0 |
| 9 | Parity is checked before timing | ✓ VERIFIED | `python_bench.py:885-923` runs CLI-vs-Python control parity, baseline exact-count equality, and control-sha equality before `measure_arm`; re-run printed `control parity OK distinct=73476107 total=129579577` before any median |
| 10 | The benchmark artifact carries module provenance | ✓ VERIFIED | `provenance.module.sha256` = measured `.so` sha `6d526431…`, plus git commit/dirty, build profile, platform, python/maturin versions; `write_json` calls `validate_schema` + `validate_provenance` before write |
| 11 | Adjacency: successive `add_from_*` calls accumulate exactly | ✓ VERIFIED | `pyo3/tests/test_counter_concurrency.py:132` (same file twice doubles every count) and `:146` (disjoint files equal concatenation) passed in the 179-test pytest run |
| 12 | Empty inputs are exact (no records, or all shorter than k) | ✓ VERIFIED | `test_counter_concurrency.py:173` record-less file adds zero and keeps `is_empty()`; passed |
| 13 | `add_sequence` feeds raw bytes to the shared extractor (D2) | ✓ VERIFIED | `counter.rs:322-331` raw `seq_str.as_bytes()` → `for_each_window`; independent run: k=7 `"ACG TACG ACGT"` → `total_kmers=0`, k=21 N-read → 0 |
| 14 | Concurrency: multi-thread `add_from_*` on one counter completes bounded and exact | ✓ VERIFIED | `test_counter_concurrency.py` 2 tests, `ThreadPoolExecutor` + 120 s `future.result(timeout=…)`, exact summed reference map; passed |
| 15 | The pre-D2 RED was captured as an executed observation | ✓ VERIFIED | `evidence/pre_d2_red_observation.json`: exit 1, four divergent cases, `python_only_total=33`, `pre_change_version_attribute=null`, head `4c97787`; red artifact sha matches |
| 16 | The rebuilt extension exports `__version__` equal to `pyproject.toml` | ✓ VERIFIED | `pyo3/src/lib.rs:57` `env!("CARGO_PKG_VERSION")`; observed `0.5.0` equals `pyo3/pyproject.toml`; `test_version.py` (no skip) passed |
| 17 | Python and CLI emit byte-identical `.rkdb` (sha `a5da813e…`) across thread configs | ✓ VERIFIED | `pyo3/tests/test_save_database_byte_identity.py` 10 tests passed; committed fixture sha256 independently recomputed as `a5da813e…` |
| 18 | The 1-vs-N byte invariant holds | ✓ VERIFIED | Same suite's 1-vs-N test collects Python t1/default and CLI t1/4/default hashes into one set; passed |
| 19 | `from_sorted_kmer_pairs` is byte-equal, sets `sorted=true`, record count = `entries.len()` | ✓ VERIFIED | `src/database/format.rs:715-751`; `tests/sorted_pairs_constructor_tests.rs` 5 tests passed (byte equality, empty, single, golden sha, descending debug panic) |
| 20 | Saved records are ascending by encoded key and thread-count independent | ✓ VERIFIED | Single `par_sort_unstable_by_key` on unique keys; 1-vs-N test passed |
| 21 | Empty-counter and error messages are preserved verbatim | ✓ VERIFIED | `SaveDatabaseError::Display` reproduces all four messages (`counter.rs:711-715`); empty-counter and directory-target tests passed |
| 22 | `src/database/format.rs` is a pure addition and `tests/fixtures/` is untouched | ✓ VERIFIED | `git diff --numstat 2fc58cb..HEAD` = `78 0`; worktree blob `dedfd95a…`; `git diff --stat … -- tests/fixtures/` empty; 12/12 manifest hashes independently verified |
| 23 | `--compare-baseline` measures t1 and default arms as fresh worker processes | ✓ VERIFIED | `python_bench.py` spawns one `--worker` subprocess per rep; re-run observed `threads_resolved=1` and `16` in the two arms |
| 24 | The verdict math is locked (inclusive 1.0 / 1.2) | ✓ VERIFIED | `MIN_SPEEDUP_T1=1.0`, `MIN_SPEEDUP_DEFAULT=1.2`, `>=` comparisons; re-run computed `PASS` from recorded medians |
| 25 | Exit contract 0/1/2 with artifact rules | ✓ VERIFIED | `EXIT_COMPARISON_RESERVED=1`; rerun exit 0 with artifact; `--threads 4` guard observed exit 2 with no artifact |
| 26 | The comparison artifact is schema+provenance validated before write | ✓ VERIFIED | `write_json` (`python_bench.py:756-765`); delivered artifact carries all required blocks |
| 27 | Host/identity guards exit 2 without an artifact | ✓ VERIFIED | `validate_baseline_identity` + pre-timing exact-count/fingerprint guards; 82 harness unit tests passed; live `--threads 4` rejection exit 2, no artifact |
| 28 | The harness unit suite covers the verdict matrix and guards | ✓ VERIFIED | `test_python_bench.py` → 82 tests OK (1 opt-in skip); `test_n_read_differential.py` → 33 tests OK |
| 29 | Post-D2 real-N labels no longer claim pre-D2 semantics; baseline immutable | ✓ VERIFIED | `REAL_N_EVIDENCE_CLASS="timing-only-real-N-post-D2"`; baseline sha `42bb480d…` equals the Phase 5 committed file; no baseline commits in `2fc58cb..HEAD` |
| 30 | `--previous` validates k/canonical/case-set and embeds a `before` block | ✓ VERIFIED | `load_previous` + `TestPreviousLoading`; re-run embedded `before` sha `6d929a45…`, `python_only_total=33`, four divergent cases |
| 31 | The docs numbers match the committed Phase 5 artifact | ✓ VERIFIED | Independently recomputed Phase 5 artifact: CLI total 37, Python total 70, delta 33, four divergent cases; docs table and README note match exactly |
| 32 | Final-tree differential artifact is PASS with the 33-key before block | ✓ VERIFIED | `evidence/n_read_differential_d2.json` (sha `599036a0…` matches gates evidence); independently reproduced |
| 33 | Final-tree benchmark artifact is PASS with module sha, baseline sha, exact counts, fingerprint | ✓ VERIFIED | `evidence/python_bench_after_d2.json` (sha `9988024a…`); module `6d526431…`, baseline `42bb480d…`, counts `129579577/73476107`, fingerprint `5cc93333…`; independently reproduced |
| 34 | The full battery is green | ✓ VERIFIED | Independently: clippy `+1.82.0 -D warnings` both crates exit 0; `cargo build --release --locked` exit 0; `cargo test --locked` exit 0 (all binaries ok); unittest discovery exit 0; version assert `0.5.0`; `pytest pyo3/tests -q` → 179 passed, 63 skipped |
| 35 | The four manifests/lockfiles are byte-identical to their Phase 8 blobs | ✓ VERIFIED | `git hash-object` = `fb5c8395…` / `7f24f3f3…` / `5b01979c…` / `6da3805f…`, exactly the pinned values |
| 36 | The frozen output contract holds | ✓ VERIFIED | 12/12 fixture hashes match `golden_manifest.sha256` (`f010e42a…`); `format.rs` worktree blob equals recorded post `dedfd95a…`; pure addition over Phase 8 `eb0d5bf2…` |
| 37 | A stale extension cannot pass the final gate | ✓ VERIFIED | `test_version.py` fails (never skips) without `__version__`; artifacts record `pyrustkmer.__file__`, module sha, git commit/dirty, binary sha; current `.so` sha matches |
| 38 | `phase9_gates_evidence.json` records every gate, pin, re-hash, and artifact sha | ✓ VERIFIED | Nine gates all `exit_code: 0`; pinned blobs; fixture manifest `f010e42a…`; all five `measured_artifacts` sha256 independently recomputed and MATCH |

**Score:** 38/38 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `pyo3/src/counter.rs` | Engine routing, D2 raw bytes, detach, single sort | ✓ VERIFIED | Substantive, wired; 487-line change |
| `pyo3/src/lib.rs` | `pyrustkmer.__version__` | ✓ VERIFIED | Line 57; observed 0.5.0 |
| `src/database/format.rs` | `from_sorted_kmer_pairs` pure addition | ✓ VERIFIED | 78 insertions, 0 deletions |
| `tests/sorted_pairs_constructor_tests.rs` | Constructor byte/header proofs | ✓ VERIFIED | 5 tests passed |
| `pyo3/tests/test_version.py` | No-skip stale-extension tripwire | ✓ VERIFIED | 2 tests passed |
| `pyo3/tests/test_public_api.py` | Exact 12-name freeze | ✓ VERIFIED | Passed |
| `pyo3/tests/test_counter_concurrency.py` | Concurrency/accumulation/empty | ✓ VERIFIED | Passed |
| `pyo3/tests/test_save_database_byte_identity.py` | Cross-surface + 1-vs-N + errors | ✓ VERIFIED | 10 passed (fixture-only arm does not require the CLI) |
| `scripts/bench/python_bench.py` | Compare mode, guards, exit contract | ✓ VERIFIED | Reproduced independently |
| `scripts/bench/tests/test_python_bench.py` | Verdict/guard/controller matrix | ✓ VERIFIED | 82 tests OK |
| `scripts/bench/n_read_differential.py` | Unified semantics + `--previous` | ✓ VERIFIED | Re-run PASS |
| `scripts/bench/tests/test_n_read_differential.py` | Previous-loading + verdicts | ✓ VERIFIED | 33 tests OK |
| `docs/user-guide/n-read-semantics.md` | D2 user documentation | ✓ VERIFIED | In both navs and index link |
| `pyo3/README.md` | Migration note with exact numbers | ✓ VERIFIED | 70→37 / 33 keys present |
| `evidence/*.json` (5 files) | Measured + audit artifacts | ✓ VERIFIED | All sha256 match gates evidence |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `pyo3/src/counter.rs` | `src/count/engine.rs` | `CountEngine::new(EngineConfig::new(k, canonical, threads, 0))` → `count_file` → `finish()?.merge_into` | ✓ WIRED | One call site each |
| `pyo3/src/counter.rs` | `src/kmer/extract.rs` | Raw `seq_str.as_bytes()` → `for_each_window` | ✓ WIRED | No strip-and-join remaining |
| `pyo3/src/lib.rs` | `pyo3/pyproject.toml` | `env!("CARGO_PKG_VERSION")` asserted in test | ✓ WIRED | 0.5.0 = 0.5.0 |
| `PyCounter::save_database` | `.rkdb` writer | `py.detach` → `get_all_counts` → `par_sort_unstable_by_key` → `from_sorted_kmer_pairs` → `write_to` | ✓ WIRED | sha `a5da813e…` |
| `python_bench.py` | `baselines/python_bench_baseline.darwin.json` | Control medians, exact counts, fingerprint | ✓ WIRED | Baseline sha `42bb480d…` |
| Controller | Fresh worker subprocess | `--worker` per (arm, rep) | ✓ WIRED | `threads_resolved` 1 / 16 observed |
| `n_read_differential.py` | Phase 5 artifact | `--previous` k/canonical/case-set validation → `before` | ✓ WIRED | Before sha `6d929a45…` |
| `docs/user-guide/n-read-semantics.md` | `mkdocs.yml` / `mkdocs.docs.yml` / `index.md` | Nav entries + index link | ✓ WIRED | Both deployed and root configs |
| `pyo3/README.md` | Measured evidence | Same 33 / 70→37 numbers | ✓ WIRED | Matches artifacts |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `PyCounter.add_from_*` | partition tables → counter | `CountEngine` reads real FASTA/FASTQ via `bio` | Yes | ✓ FLOWING |
| `PyCounter.save_database` | `pairs` | `counter.get_all_counts()` snapshot | Yes | ✓ FLOWING |
| Differential Python map | count map | `PyCounter.add_from_fastq` + `get_all_counts` | Yes | ✓ FLOWING |
| Differential CLI map | count map | CLI `.rkdb` decoded through `PyDatabase` | Yes | ✓ FLOWING |
| Benchmark arms | wall-clock + counts | Fresh worker `PyCounter` runs on 1M-read control | Yes | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Extension version tripwire | `.venv313/bin/python -c "import pyrustkmer; print(pyrustkmer.__version__)"` | `0.5.0` | ✓ PASS |
| D2 whitespace skip | `.venv313/bin/python -c "PyCounter(7).add_sequence('ACG TACG ACGT')"` | `total_kmers=0` | ✓ PASS |
| N-read differential | `.venv313/bin/python scripts/bench/n_read_differential.py --expect-unified --previous … --out /tmp/…` | `result=PASS … divergent=0`, exit 0 | ✓ PASS |
| Benchmark comparison | `.venv313/bin/python scripts/bench/python_bench.py --mode slice … --compare-baseline …` | `PASS speedup_t1=2.2682 speedup_default=8.5479`, exit 0 | ✓ PASS |
| Compare-mode invalid threads | `… --threads 4 --compare-baseline …` | exit 2, no artifact | ✓ PASS |
| Public API freeze | `.venv313/bin/python -c "dir(pyrustkmer.PyCounter)"` | exactly 12 names | ✓ PASS |
| pytest suite | `.venv313/bin/python -m pytest pyo3/tests -q` | 179 passed, 63 skipped | ✓ PASS |
| Harness discovery | `python3 -m unittest discover -s scripts/bench/tests -t .` | exit 0 | ✓ PASS |
| Fixture manifest | 12 sha256 comparisons against `golden_manifest.sha256` | 12 ok, 0 bad | ✓ PASS |
| Full Rust battery | clippy 1.82 both crates, release build, `cargo test --locked` | all exit 0 | ✓ PASS |

### Probe Execution

Not applicable — Phase 9 declares and ships no probes (`find scripts -path '*/tests/probe-*.sh'` is empty; no probe paths in PLAN/SUMMARY).

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| PY-01 | 09-01, 09-02, 09-05 | Engine-routed PyCounter file methods; frozen API; `py.detach` on parallel/blocking paths; `save_database` double-sort fixed | ✓ SATISFIED | Truths 1-5, 11-14, 16-22, 34-38 |
| PY-02 | 09-01, 09-03, 09-04, 09-05 | D2 skip-N in Python; documented output change; measured win vs PROF-04 baseline | ✓ SATISFIED | Truths 6-10, 13, 15, 23-33 |

**Orphaned requirements:** none — `REQUIREMENTS.md` maps only PY-01 and PY-02 to Phase 9, and every plan declares them (`09-01`/`09-05` both, `09-02` PY-01, `09-03`/`09-04` PY-02).

### Prohibitions (must-NOT)

| # | Prohibition | Verdict | Evidence |
|---|-------------|---------|----------|
| 1 | 09-01: MUST NOT weaken pre-D2 tests into vacuous smoke checks | ✓ SATISFIED | `_strip_join_counts` retained; `test_fixture_still_exercises_d2_not_strip_and_join` asserts inequality in both rewritten classes; suite passes |
| 2 | 09-01: MUST NOT expose new Python-visible state/API — no skipped-window counter/getter, no new method names, no new required constructor args; 12 frozen names | ✓ SATISFIED | `dir(PyCounter)` = exactly 12; no skipped-window API; constructor unchanged. Note: the WR-02 fix added a read-only `PyCounterStats.threads` introspection field — additive on the stats object, not a `PyCounter` member; within the prohibition's enumerated scope |
| 3 | 09-02: MUST NOT edit/regenerate/re-pin fixtures, manifest, or frozen writers | ✓ SATISFIED | `tests/fixtures/` diff empty; 12/12 hashes match; writers untouched |
| 4 | 09-03: MUST NOT edit/re-pin the Phase 5 baseline or relax 1.0/1.2 thresholds | ✓ SATISFIED | Baseline sha `42bb480d…`; no baseline commits in range; thresholds unchanged |
| 5 | 09-04: MUST NOT ship D2 without documented exact before/after numbers (docs page, docstrings, README) | ✓ SATISFIED | All three surfaces carry 70→37 / 33 / four-case evidence, verified against the committed artifact |

These are judgment-tier prohibitions (no `verification` field in the plan frontmatter); the verdicts above are LLM judgments grounded in the cited code and executed commands.

### Code Review Findings (IN-01..IN-08)

The 4 warnings were fixed and revalidated (`72a8399`, `266492a`, `669e91f`, `af4d954`). The 8 info findings were evaluated against the must-haves:

| ID | Finding | Assessment |
|----|---------|------------|
| IN-01 | Preservation gates also pass on the parent implementation | Does not undermine truth 3: the single-sort change is a static call-site property, verified directly (`par_sort_unstable_by_key` once, `from_sorted_kmer_pairs` once, zero stable sorts). Test-level counter would be hardening only |
| IN-02 | Stale test docstring mentions `LocalKmerCounts` | Non-user-facing comment; no must-have depends on it. Info |
| IN-03 | Non-linearizable `save_database` snapshot undocumented | Snapshot semantics are accepted by the phase design; no must-have requires linearizability. Info |
| IN-04 | `--previous` accepts any structurally valid differential (no sha pin) | Must-have only requires k/canonical/case-set validation, which is implemented and tested. Defense-in-depth suggestion |
| IN-05 | `record_boundary` case cannot detect cross-record joins post-D2 | The doc claim "windows never span record boundaries" is true by per-record `count_sequence` and covered by N-free multi-record unit tests; the differential case is not the contract. Info |
| IN-06 | `test_missing_extension_exits_2` fails under `.venv313` | The documented gate uses system `python3`; independently re-run here: 33 tests OK. Pre-existing fragility in one test, not a must-have gate |
| IN-07 | `SaveDatabaseError::Database` unreachable | Harmless defensive arm; the four verbatim messages are preserved |
| IN-08 | Compare mode accepts `--reps 1` / ignores CV warnings | Delivered run used 3 reps with CV 1.15% / 1.76% (no `cv_warning`); must-have does not mandate a minimum rep count. Gate-hardening suggestion |

**None of IN-01..IN-08 undermines any must-have or blocks the phase goal.**

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| — | — | `TBD` / `FIXME` / `XXX` | — | None in any phase-modified file (ripgrep clean) |
| `src/database/format.rs` | 1481-1612 | `placeholder` comments | ℹ Info | Pre-existing writer-protocol terminology, not a debt marker; untouched by this phase |
| `pyo3/tests/test_counter.py` | ~1121 | Stale docstring (`LocalKmerCounts`) | ℹ Info | IN-02; documentation only, no behavioral impact |

### Decision Coverage

No trackable decisions in CONTEXT.md.

(The handler skipped the heuristic: zero trackable decision entries. The phase's locked decisions were nevertheless cross-checked manually against the shipped code and evidence — engine routing, `initial_capacity=0`, D2 scope, single-sort + detach, dual-thread comparison, documented numbers, and no CI gate — and all are honored.)

### Gaps Summary

None. All four roadmap success criteria are observably true in the codebase and were independently re-executed, not merely read from the SUMMARY files:

1. Engine routing, frozen 12-name API, and the removed double sort are present in `pyo3/src/counter.rs` / `src/database/format.rs`.
2. All three parallel/blocking paths detach with owned `Send` captures; no `allow_threads` remains; the rebuilt `0.5.0` extension is version-asserted before pytest.
3. The D2 differential re-runs to `PASS` with zero divergence, and the change is documented in a nav-wired user-guide page and the README migration note with exact verified numbers.
4. The benchmark re-runs to `PASS` at 2.27x (t1) / 8.55x (default) against the immutable Phase 5 baseline, with parity-before-timing and module provenance.

### Evidence Notes

- **Known pre-existing flake:** `scripts/bench/tests/test_verify_threads.py::TestNegativeControls::test_pre_engine_n_plus_one_stub_is_measured_red` — macOS `sample` race (~50%). `git log 2fc58cb..HEAD -- …/verify_threads.py scripts/bench/tests/test_verify_threads.py` is empty; the full discovery passed on this run. Not a phase regression.
- **Stale-build incident:** the final evidence was generated on `bf8a09f`; `git diff bf8a09f..HEAD -- . ':!.planning'` is empty, so the code tree is identical to the current HEAD. The measured module sha (`6d526431…`) and CLI binary sha (`f6ace9f…`) match the current artifacts, and the version assert / pytest gates pass on the current tree. The final evidence reflects the final tree.
- **`git_dirty` in the benchmark artifact:** the benchmark's own `provenance.git_dirty` was `true` only because the three evidence files were being rewritten; `phase9_gates_evidence.json` records `git_dirty_paths_outside_evidence: []`. The independent re-run on the committed HEAD reports `git_dirty: false`.

### Human Verification Required

None — all four success criteria were verified by code inspection and independent command re-execution; no visual, real-time, or external-service behavior is involved.

---

_Verified: 2026-11-13T03:16:01Z_
_Verifier: Claude (gsd-verifier)_
