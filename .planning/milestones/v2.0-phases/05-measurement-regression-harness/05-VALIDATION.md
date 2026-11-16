---
phase: "05"
slug: "measurement-regression-harness"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
status: validated
nyquist_compliant: true
wave_0_complete: true
created: "2026-11-16"
validated: "2026-11-16"
---

# Phase 05 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> **Reconstructed post-execution** (validate-phase State B, 2026-11-16): the phase executed 2026-11-12 without a seeded VALIDATION.md; this record was audited from the archived artifacts (7 PLANs, 7 SUMMARYs, `05-VERIFICATION.md` re-run 2026-11-14 at 12/12 passed) and the test files on disk. It closes the v2.0 milestone-audit Nyquist coverage gap (HYG-02).

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Python stdlib `unittest` (`scripts/bench/tests/`, harness contract: stdlib-only) + Rust `cargo test` (integration suites) + `proptest` 1.5 |
| **Config file** | `Cargo.toml` (root), `pyo3/pyproject.toml` (`[tool.pytest.ini_options]`) — no config needed for stdlib unittest discovery |
| **Quick run command** | `python3 -m unittest discover -s scripts/bench/tests -t . -k <module>` |
| **Full suite command** | `cargo test --locked` + `python3 -m unittest discover -s scripts/bench/tests -t .` |
| **Harness gates** | `scripts/bench/bench.py --mode slice ... --parity-only` (pinned head-4M parity); `scripts/bench/thread_scaling.py --mode synthetic --reads 500000 --reps 3` (PROF-02 standing gate); `scripts/bench/capture_goldens.py` (non-regenerating fixture rehash) |
| **Estimated runtime** | harness suite ~12 s; full `cargo test --locked` ~5-8 min |

---

## Sampling Rate

- **After every task commit:** the touched test module + `python3 -m unittest discover -s scripts/bench/tests -t . -k <module>`
- **After every plan wave:** full suite (`cargo test --locked` + harness discovery)
- **Before `/gsd-verify-work`:** full suite green; pinned parity gate green; thread-scaling standing gate verdict GREEN on a fresh measurement
- **Max feedback latency:** ~8 minutes

---

## Per-Task Verification Map

Reconstructed 2026-11-16 from plan frontmatter declarations and `05-VERIFICATION.md` (re-verified 2026-11-14 against the post-Phase-10 tree, 12/12 truths, digest `ee504391…`).

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 05-01-* | 01 | 1 | PROF-01, PROF-02 | T-04-02/03 stance | Pinned parity (229,694,874 / 519,271,168) before timing; provenance on every artifact (`binary_provenance` :345, `validate_provenance` :378) | integration (dev host) | `bench.py --mode slice --parity-only` vs `baselines/slice_parity.crr1936095.json` | ✅ | ✅ green (gate re-run exit 0, verification truth 1) |
| 05-02-* | 02 | 1 | PROF-01 | — | Random-record subslice selection bound by manifest (`provision_random_slice` :615, `selection_identity_from` :990) | unit + integration | `unittest ... -k test_degradation`; slice gate-proof | ✅ (28411ad-lineage files) | ✅ green |
| 05-03-* | 03 | 1 | PROF-02 | — | Thread-scaling gate records t1/t4/t16 with `rotation_schedule` (:100) / `scaling_verdict` (:126); exit 0/1/2 | e2e/benchmark | `thread_scaling.py --current` vs `thread_scaling_baseline.json` | ✅ `tests/test_thread_scaling.py` | ✅ green (RED baseline re-verdict exit 1 = expected; fresh measurement GREEN exit 0, verification truth 3) |
| 05-04-* | 04 | 1 | PROF-01 | — | Golden `.rkdb` fixtures non-regenerating; 12-fixture manifest rehash only | differential | `capture_goldens.py`; `cargo test --locked --test golden_sha256_tests` | ✅ | ✅ green (truth 8: 12/12 hashes match, script never regenerates) |
| 05-05-* | 05 | 1 | PROF-03 | — | Contention microbench: 4 variants × t1/t4/t16 × 3 counterbalanced rounds, per-arm conservation | benchmark | `contention_bench.py`; `unittest ... -k test_contention_bench` | ✅ | ✅ green (`contention_evidence.json` 36/36 `conservation_ok`, attribution-v1 persisted) |
| 05-06-* | 06 | 1 | PROF-04, PROF-05 | — | Python-surface benchmark baseline (identity-validated) + N-read differential (control equal, divergence quantified) | unit + integration | `unittest ... -k test_python_bench`; `n_read_differential.py` | ✅ | ✅ green (`validate_baseline_identity → OK`; differential 9/9 cases, verification truths 5/6) |
| 05-07-* | 07 | 1 | PROF-01, PROF-02, PROF-04 | T-04-06 stance | Gates wired into CI without softeners (`benchmark.yml:90/121/136/150`; zero `continue-on-error`) | e2e (CI) | push; `benchmark.yml` must pass; `--current` verdict step | ✅ | ✅ green (verification truth 7: no workflow silencing; gate chain unconditional) |
| — | — | — | PROF-01..05 (coverage) | — | Schema-v1 committed baselines remain loadable under unchanged `validate_schema` | unit | `unittest ... -k test_schema` | ✅ | ✅ green (verification truth 11) |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

Known pre-existing red NOT in this phase's map: `scripts/bench/tests/test_phase10_verdict.py` (3 tests) reads `.planning/phases/10-benchmark-verdict/` paths moved to `.planning/milestones/v2.0-phases/` by commit 97c497c — tracked in STATE.md blockers / 11-01 deferred-items.md, path-retarget pending; unrelated to PROF-01..05 (Phase 10 artifact, not a Phase 5 requirement).

---

## Wave 0 Requirements

- [x] `scripts/bench/tests/test_thread_scaling.py`, `test_verify_threads.py`, `test_contention_bench.py`, `test_python_bench.py`, `test_n_read_differential.py`, `test_degradation.py`, `test_schema.py` — delivered during execution (all exist at HEAD)
- [x] `tests/thread_pool_size_tests.rs` — thread-reality instrument (RED at Phase 5 close by design; GREEN after Phase 6/7 fix, as intended)
- [x] `scripts/bench/baselines/{thread_scaling_baseline.json, slice_parity.crr1936095.json, python_bench_baseline.darwin.json}` — committed, unchanged since Phase 5
- [x] `.planning/research/profiling/{microbench_Cargo.toml, microbench_main.rs, verify_threads.py}` + committed `microbench_Cargo.lock`
- [x] Evidence JSONs beside archived artifacts: `thread_reality_evidence.json`, `contention_evidence.json`, `golden_capture.json`, `n_read_differential.json`, `slice_parity_evidence.json`
- [x] No framework install needed (stdlib unittest + existing cargo tooling)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions | Outcome |
|----------|-------------|------------|-------------------|---------|
| Real-data slice parity on the pinned head-4M selection (CRR1936095 part, ~minutes of wall + jellyfish round-trip) | PROF-01 | Requires the local dataset and jellyfish; CI carries no dataset | `bench.py --mode slice --input CRR1936095_r1.part_001.fq.gz --slice-selection head --slice-reads 4000000 --k 21 --parity-only` | **DONE 2026-11-14** — re-run at verification: exit 0, `PARITY OK distinct=229694874 total=519271168`, `PARITY REFERENCE OK` (verification truth 1) |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (none remained at phase close)
- [x] No watch-mode flags
- [x] Feedback latency < 8 min
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** validated 2026-11-16 — reconstructed from archived artifacts; grounding: `05-VERIFICATION.md` re-verification 2026-11-14 (12/12 truths, 0 behavior-unverified, digest `ee504391…`), harness suite re-run 2026-11-16 (phase-5 modules green), per-plan requirement frontmatter greps match the verification report's coverage row.

## Validation Audit 2026-11-16

| Metric | Count |
|---|---|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |
