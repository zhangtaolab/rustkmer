---
phase: "9"
slug: "python-parity"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
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

Pre-change baselines recorded 2026-11-13: pytest `158 passed, 63 skipped`; harness `Ran 361 tests … OK (skipped=1)`.

---

## Sampling Rate

- **After every task commit:** Run the quick run command, plus the task-specific pytest file when the task touches `pyo3/`.
- **After every plan wave:** Rebuild the extension (`env -u CONDA_PREFIX VIRTUAL_ENV=.venv313 … maturin develop --release -m pyo3/Cargo.toml`), assert `pyrustkmer.__version__`, then `pytest pyo3/tests -q` plus the harness unittest discovery.
- **Before `/gsd-verify-work`:** Full suite green, plus the four golden/output test binaries, the `--expect-unified` differential, the `--compare-baseline` benchmark, the byte-identity pytest, and the concurrency pytest.
- **Max feedback latency:** 600 seconds per task (quick run plus the touched test file); the full battery in the Validation Sign-Off is a phase gate measured at ~7–12 minutes, so it is not counted as per-task feedback.

---

## Per-Task Verification Map

Task IDs are assigned by each `PLAN.md`; this table is seeded at requirement level and reconciled task-by-task at `validate-phase`.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD | TBD | TBD | PY-01 #1 | — | Engine routing: `CountEngine::new` + `count_file` + `merge_into` present, no `reader.lines()` counting loop | static + integration | `grep -q "CountEngine::new" pyo3/src/counter.rs && grep -q "count_file(" pyo3/src/counter.rs && grep -q "merge_into" pyo3/src/counter.rs && ! grep -n "reader.lines()" pyo3/src/counter.rs` | ✅ source change | ⬜ pending |
| TBD | TBD | TBD | PY-01 #1 | — | Public `PyCounter` surface frozen at 12 names | unit | `.venv313/bin/python -m pytest pyo3/tests/test_public_api.py -q` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | PY-01 #1 | — | `save_database` sorts exactly once via `par_sort_unstable_by_key`, no `from_kmer_pairs`/`sort_by_key` | static + unit | `test "$(grep -c 'par_sort_unstable_by_key' pyo3/src/counter.rs)" -eq 1 && ! grep -n "from_kmer_pairs\|sort_by_key" pyo3/src/counter.rs`; `cargo test --locked --test sorted_pairs_constructor_tests` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | PY-01 #1 | T-9-supply | `save_database` bytes == CLI == committed golden; 1-vs-N invariant | integration | `.venv313/bin/python -m pytest pyo3/tests/test_save_database_byte_identity.py -q` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | PY-01 #2 | T-9-gil | `py.detach` only; no `allow_threads`; `Ungil`-clean | static + compile | `test "$(grep -c 'py.detach' pyo3/src/counter.rs)" -ge 3 && ! grep -n "allow_threads" pyo3/src/counter.rs`; `cargo +1.82.0 clippy --locked --all-targets --manifest-path pyo3/Cargo.toml -- -D warnings` | ✅ source change | ⬜ pending |
| TBD | TBD | TBD | PY-01 #2 | T-9-gil | No GIL deadlock under concurrent `add_from_*`; exact counts | integration | `.venv313/bin/python -m pytest pyo3/tests/test_counter_concurrency.py -q` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | PY-01 #2 | T-9-stale | Rebuilt extension is version-asserted before pytest | command gate | `maturin develop --release -m pyo3/Cargo.toml` then `.venv313/bin/python -c "import pyrustkmer, tomllib; assert pyrustkmer.__version__ == tomllib.load(open('pyo3/pyproject.toml','rb'))['project']['version']"`; `pytest pyo3/tests/test_version.py -q` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | PY-02 #3 | — | D2 skip-N unified across FASTA/FASTQ/sequence, k 21/64, canonical on/off | unit | `.venv313/bin/python -m pytest pyo3/tests -q -k "NReadSkipParity or Whitespace"` | ✅ update existing | ⬜ pending |
| TBD | TBD | TBD | PY-02 #3 | — | Cross-surface divergence eliminated (all four cells equal, totals 0/0/0) | differential | `.venv313/bin/python scripts/bench/n_read_differential.py --expect-unified --previous .planning/phases/05-measurement-regression-harness/n_read_differential.json --rustkmer target/release/rustkmer --out .planning/phases/09-python-parity/evidence/n_read_differential_d2.json` | ❌ `--previous` W0 | ⬜ pending |
| TBD | TBD | TBD | PY-02 #3 | — | Docs state the change with numbers (33 chimeric → 0) | docs gate | `test -f docs/user-guide/n-read-semantics.md && grep -q "n-read-semantics.md" mkdocs.yml && grep -qi "skip-N" docs/user-guide/n-read-semantics.md pyo3/README.md pyo3/src/counter.rs` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | PY-02 #4 | T-9-bench | Measured win vs Phase 5 baseline: t1 ≥ 1.0x, default ≥ 1.2x on the N-free control | benchmark | `.venv313/bin/python scripts/bench/python_bench.py … --compare-baseline scripts/bench/baselines/python_bench_baseline.darwin.json` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | PY-02 #4 | T-9-bench | Comparison exit contract 0/1/2 + host/fingerprint guards | harness unit | `python3 -m unittest discover -s scripts/bench/tests -t . -p 'test_python_bench.py' -v` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | Regression | — | Frozen writer bytes / goldens unchanged | golden | `cargo test --locked --test golden_sha256_tests --test golden_tests --test rkdb_v2_byte_identity_tests --test output_pipeline_tests` | ✅ existing | ⬜ pending |
| TBD | TBD | TBD | Regression | T-9-supply | Manifests/lockfiles byte-unchanged | command | `test -z "$(git diff --stat -- Cargo.toml Cargo.lock pyo3/Cargo.toml pyo3/Cargo.lock)"` | ✅ existing | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `pyo3/tests/test_public_api.py` — pins the 12-name `PyCounter` surface (PY-01 #1)
- [ ] `pyo3/tests/test_save_database_byte_identity.py` — CLI/Py/golden sha256 + 1-vs-N (PY-01 #1)
- [ ] `pyo3/tests/test_version.py` — stale-extension/version assert (PY-01 #2)
- [ ] `pyo3/tests/test_counter_concurrency.py` — concurrent `add_from_*` with timeout and exact counts (PY-01 #2)
- [ ] `tests/sorted_pairs_constructor_tests.rs` — `from_sorted_kmer_pairs` byte equality vs `from_kmer_pairs` (PY-01 #1)
- [ ] `scripts/bench/tests/test_python_bench.py` — `--compare-baseline` exit 0/1/2 cases and host/fingerprint guards (PY-02 #4)
- [ ] `scripts/bench/tests/test_n_read_differential.py` — `--previous` loading/validation + updated `EXPECTED_SEMANTICS` (PY-02 #3)
- [ ] `docs/user-guide/n-read-semantics.md` + `mkdocs.yml` nav + `docs/user-guide/index.md` link (PY-02 #3)
- [ ] `pyo3/README.md` migration note (PY-02 #3)

No framework install needed: pytest, maturin, numpy are already present in `.venv313`.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `mkdocs build --strict` renders the new N-read page | PY-02 #3 | The `section-index` plugin is missing on this host, so a strict build exits 1 for reasons unrelated to this phase | Confirm the file exists, is listed in `mkdocs.yml` nav, and is linked from `docs/user-guide/index.md`; optionally run a non-strict build and inspect the rendered page |
| Full-human-scale Python timing | PY-02 #4 | Reserved for Phase 10 (BENCH-V2-02); this phase uses the committed slice baseline | Run `python_bench.py --compare-baseline` on the dev host and confirm the recorded medians |

*All other phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 600s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
