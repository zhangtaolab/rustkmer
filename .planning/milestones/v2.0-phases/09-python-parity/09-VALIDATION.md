---
phase: "9"
slug: "python-parity"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: validated
nyquist_compliant: true
wave_0_complete: true
created: "2026-11-13"
---

# Phase 9 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Rust: `cargo test` (built-in, `--locked`); Python: pytest 9.0.2 in `.venv313`; harness: stdlib `unittest` discovery |
| **Config file** | `pyo3/pyproject.toml` `[tool.pytest.ini_options]` (testpaths `tests`, `addopts = ["-v"]`); Rust uses defaults |
| **Quick run command** | `cargo test --locked --test count_engine_tests --test output_pipeline_tests && python3 -m unittest discover -s scripts/bench/tests -t .` |
| **Full suite command** | `cargo +1.82.0 clippy --locked --all-targets -- -D warnings && cargo +1.82.0 clippy --locked --all-targets --manifest-path pyo3/Cargo.toml -- -D warnings && cargo build --release --locked && cargo test --locked && .venv313/bin/python -m pytest pyo3/tests -q` |
| **Estimated runtime** | ~7–12 min (full); ~90 s (quick) |

Baselines at phase start (2026-11-13): pytest `158 passed, 63 skipped`; harness `Ran 361 tests … OK (skipped=1)`.
Final-tree results: Rust `508 passed / 0 failed`; pytest `177 passed, 63 skipped`; harness `398 tests, OK (skipped=1)`.

---

## Sampling Rate

- **After every task commit:** Run the quick run command, plus the task-specific pytest file when the task touches `pyo3/`.
- **After every plan wave:** Rebuild the extension (`env -u CONDA_PREFIX VIRTUAL_ENV=.venv313 … maturin develop --release -m pyo3/Cargo.toml`), assert `pyrustkmer.__version__`, then `pytest pyo3/tests -q` plus the harness unittest discovery.
- **Before `/gsd-verify-work`:** Full suite green, plus the four golden/output test binaries, the `--expect-unified` differential, the `--compare-baseline` benchmark, the byte-identity pytest, and the concurrency pytest.
- **Max feedback latency:** 600 seconds per task (quick run plus the touched test file); the full battery in the Validation Sign-Off is a phase gate measured at ~7–12 minutes, so it is not counted as per-task feedback.

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 09-01-T1 | 09-01 | 1 | PY-01 #1 | — | Engine routing: `CountEngine::new` + `count_file` + `merge_into` present, no `reader.lines()` counting loop | static + integration | `grep -q "CountEngine::new" pyo3/src/counter.rs && grep -q "count_file(" pyo3/src/counter.rs && grep -q "merge_into" pyo3/src/counter.rs && ! grep -n "reader.lines()" pyo3/src/counter.rs` | ✅ | ✅ green |
| 09-01-T1 | 09-01 | 1 | PY-01 #2 | T-9-gil | `py.detach` only; no `allow_threads`; `Ungil`-clean | static + compile | `test "$(grep -c 'py.detach' pyo3/src/counter.rs)" -ge 3 && ! grep -n "allow_threads" pyo3/src/counter.rs`; `cargo +1.82.0 clippy --locked --all-targets --manifest-path pyo3/Cargo.toml -- -D warnings` | ✅ | ✅ green |
| 09-01-T1 | 09-01 | 1 | PY-02 #3 | — | Pre-D2 RED captured as an executed observation (exit 1, 4 divergent cases, 33 chimeric keys) before any binding edit | evidence | `python3 scripts/bench/n_read_differential.py --expect-unified ...` → exit 1, recorded in `evidence/pre_d2_red_observation.json` | ✅ | ✅ green |
| 09-01-T2 | 09-01 | 1 | PY-01 #1 | — | Public `PyCounter` surface frozen at 12 names | unit | `.venv313/bin/python -m pytest pyo3/tests/test_public_api.py -q` | ✅ | ✅ green |
| 09-01-T2 | 09-01 | 1 | PY-01 #2 | T-9-gil | No GIL deadlock under concurrent `add_from_*`; exact counts; same-file-twice = 2x; record-less file leaves `is_empty()` | integration | `.venv313/bin/python -m pytest pyo3/tests/test_counter_concurrency.py -q` | ✅ | ✅ green |
| 09-01-T2 | 09-01 | 1 | PY-01 #2 | T-9-stale | Rebuilt extension is version-asserted before pytest | command gate | `maturin develop --release -m pyo3/Cargo.toml` then `.venv313/bin/python -c "import pyrustkmer; assert pyrustkmer.__version__ == '0.5.0'"`; `.venv313/bin/python -m pytest pyo3/tests/test_version.py -q` | ✅ | ✅ green |
| 09-01-T3 | 09-01 | 1 | PY-02 #3 | — | D2 skip-N unified across FASTA/FASTQ/sequence, k 21/64, canonical on/off, with old-vs-new anti-softening assertions | unit | `.venv313/bin/python -m pytest pyo3/tests -q -k "NReadSkipParity or Whitespace"` | ✅ | ✅ green |
| 09-02-T1 | 09-02 | 2 | PY-01 #1 | — | `from_sorted_kmer_pairs` is a pure addition and byte-equal to `from_kmer_pairs` | unit | `cargo test --locked --test sorted_pairs_constructor_tests`; `git diff --numstat` deletions == 0 | ✅ | ✅ green |
| 09-02-T2 | 09-02 | 2 | PY-01 #1 | T-9-supply | `save_database` sorts exactly once via `par_sort_unstable_by_key`, no `from_kmer_pairs`/`sort_by_key`; bytes == CLI == committed golden; 1-vs-N invariant | static + integration | `test "$(grep -c 'par_sort_unstable_by_key' pyo3/src/counter.rs)" -eq 1 && ! grep -n "from_kmer_pairs\|sort_by_key" pyo3/src/counter.rs`; `.venv313/bin/python -m pytest pyo3/tests/test_save_database_byte_identity.py -q` | ✅ | ✅ green |
| 09-03-T1 | 09-03 | 2 | PY-02 #4 | T-9-bench | `--compare-baseline` measures t1 + default arms with pre-timing parity guards, inclusive 1.0/1.2 thresholds, 0/1/2 exit contract | benchmark | `.venv313/bin/python scripts/bench/python_bench.py … --compare-baseline scripts/bench/baselines/python_bench_baseline.darwin.json` | ✅ | ✅ green |
| 09-03-T2 | 09-03 | 2 | PY-02 #4 | T-9-bench | Comparison verdict/guard/controller unit suite (exit 0 writes, exit 1 writes with verdict, every exit 2 writes nothing) | harness unit | `python3 -m unittest discover -s scripts/bench/tests -t . -p 'test_python_bench.py' -v` | ✅ | ✅ green |
| 09-03-T3 | 09-03 | 2 | PY-02 #3 | — | Retired pre-D2 label removed from operator docs; post-D2 label documented; exit contract anchored | docs gate | anchored greps over `scripts/bench/README.md` | ✅ | ✅ green |
| 09-04-T1 | 09-04 | 2 | PY-02 #3 | — | `--previous` loads and strictly validates the immutable pre-D2 artifact; never overwrites it | harness unit | `python3 -m unittest discover -s scripts/bench/tests -t . -p 'test_n_read_differential.py' -v` | ✅ | ✅ green |
| 09-04-T2 | 09-04 | 2 | PY-02 #3 | — | Docs state the change with numbers (33 chimeric → 0) in all three surfaces | docs gate | `test -f docs/user-guide/n-read-semantics.md && grep -q "n-read-semantics.md" mkdocs.yml && grep -qi "skip-N" docs/user-guide/n-read-semantics.md pyo3/README.md pyo3/src/counter.rs` | ✅ | ✅ green |
| 09-05-T1 | 09-05 | 3 | PY-02 #3, PY-02 #4 | T-9-bench | Final-tree differential unified (9/9 equal, 0 divergence) and measured win recorded (t1 2.30x, default 8.48x) | evidence | `evidence/n_read_differential_d2.json`, `evidence/python_bench_after_d2.json` | ✅ | ✅ green |
| 09-05-T2 | 09-05 | 3 | Regression | T-9-supply | Full battery 9/9 exit 0; frozen writer bytes/goldens unchanged; manifests/lockfiles byte-unchanged | golden + command | `cargo test --locked --test golden_sha256_tests --test golden_tests --test rkdb_v2_byte_identity_tests --test output_pipeline_tests`; `test -z "$(git diff --stat -- Cargo.toml Cargo.lock pyo3/Cargo.toml pyo3/Cargo.lock)"` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `pyo3/tests/test_public_api.py` — pins the 12-name `PyCounter` surface (PY-01 #1)
- [x] `pyo3/tests/test_save_database_byte_identity.py` — CLI/Py/golden sha256 + 1-vs-N (PY-01 #1)
- [x] `pyo3/tests/test_version.py` — stale-extension/version assert (PY-01 #2)
- [x] `pyo3/tests/test_counter_concurrency.py` — concurrent `add_from_*` with timeout and exact counts (PY-01 #2)
- [x] `tests/sorted_pairs_constructor_tests.rs` — `from_sorted_kmer_pairs` byte equality vs `from_kmer_pairs` (PY-01 #1)
- [x] `scripts/bench/tests/test_python_bench.py` — `--compare-baseline` exit 0/1/2 cases and host/fingerprint guards (PY-02 #4)
- [x] `scripts/bench/tests/test_n_read_differential.py` — `--previous` loading/validation + updated `EXPECTED_SEMANTICS` (PY-02 #3)
- [x] `docs/user-guide/n-read-semantics.md` + `mkdocs.yml` nav + `docs/user-guide/index.md` link (PY-02 #3)
- [x] `pyo3/README.md` migration note (PY-02 #3)

No framework install needed: pytest, maturin, numpy are already present in `.venv313`.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `mkdocs build --strict` renders the new N-read page | PY-02 #3 | The `section-index` plugin is missing on this host, so a strict build exits 1 for reasons unrelated to this phase. The automated gate covers file existence, nav membership, index link, and content. | Confirm the file exists, is listed in `mkdocs.yml` nav, and is linked from `docs/user-guide/index.md`; optionally run a non-strict build and inspect the rendered page |
| Full-human-scale Python timing | PY-02 #4 | Explicitly deferred to Phase 10 (BENCH-V2-02); the Phase 9 requirement is the committed slice baseline, which is automated | Run `python_bench.py --compare-baseline` on the dev host and confirm the recorded medians |

*Both manual rows are environmental or out-of-phase; every Phase 9 requirement has automated verification.*

---

## Validation Audit

| Gaps found | Resolved | Escalated |
|------------|----------|-----------|
| 0 | 0 | 0 |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 600s per task
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-11-13

## Validation Audit 2026-11-13

| Metric | Count |
|---|---|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |
