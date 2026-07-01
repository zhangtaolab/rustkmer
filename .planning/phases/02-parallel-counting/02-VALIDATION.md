---
phase: 2
slug: parallel-counting
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-07-01
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Derived from `02-RESEARCH.md` §Validation Architecture.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | `cargo test` (built-in) + `proptest 1.5` (dev-dep) + `pytest 8.4+` (pyo3/tests/) |
| **Config file** | Root: inline `#[cfg(test)]`; pyo3: `pyo3/pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `cargo test --test parallel_count_tests` |
| **Full suite command** | `cargo test` (root) && `cargo test` (pyo3) && `maturin develop && pytest pyo3/tests/` |
| **Estimated runtime** | quick ~15s · full ~60–120s (pyo3 wheel build dominates) |

---

## Sampling Rate

- **After every task commit:** `cargo test --test parallel_count_tests` + `cargo clippy -D warnings` (the Phase-1 FOUND-01 gate MUST stay green on both crates)
- **After every plan wave:** `cargo test` (root) + `cargo test` (pyo3) + `maturin develop && pytest pyo3/tests/`
- **Before `/gsd-verify-work`:** Full suite green; differential test passes for all D-13 cells (`k ∈ {21,32,64}` × canonical × ≥2 thread counts)
- **Max feedback latency:** ~15s (quick subset)

---

## Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | Wave 0? |
|--------|----------|-----------|-------------------|---------|
| PCOUNT-01 | `count --threads N` uses N; default uses num_cpus; `RUSTKMER_THREADS`/`RAYON_NUM_THREADS` precedence (D-07) | unit + integration | `cargo test --test parallel_count_tests -- test_thread_resolution` | ❌ Wave 0 (plan 02-04) |
| PCOUNT-02 | DashMap swap compiles; `increment` atomic per-key; overflow still errors at u32::MAX | unit (inline `src/hash/table.rs`) | `cargo test --lib hash::table::tests` | ✅ existing, extend |
| PCOUNT-03 | `PyCounter(k, canonical, threads=4)` releases GIL; counting parallelizes | integration (pytest) | `pytest pyo3/tests/test_counter.py` (parallel cases) | ❌ Wave 0 (plan 02-04) |
| PCOUNT-04 | `--threads 1` vs `--threads N` produce identical count maps (D-10 differential) | integration (differential) | `cargo test --test parallel_count_tests -- differential_threads_1_vs_n` | ❌ Wave 0 (plan 02-04) |
| (cross-cutting) | Default-sort (D-09) yields deterministic output run-to-run | integration | `cargo test --test parallel_count_tests -- deterministic_sorted_output` | ❌ Wave 0 (plan 02-04) |

### Differential Test Dimensions (guard PCOUNT-04)

| Axis | Values | Why |
|------|--------|-----|
| Thread count | `{1, 2, N}` (N = num_cpus) | 1 = sequential baseline; 2 = simplest races; N = shard stress |
| k-mer width | `{21, 32, 64}` | D-13 matrix; u128 at all bit-fill densities |
| Canonical | `{true, false}` | D-13; canonical adds per-record compute interleaving with increment |
| Input scale | `{tiny fixture, medium slice, large}` | tiny = fast feedback; large = stress (CRR1936095 slice if present) |
| Input shape | `{FASTA, FASTQ, gzipped}` | covers both `process_*_file` parallel paths + gzip producer |

**The commutativity property:** counting is integer addition (commutative + associative), so the final count per k-mer is mathematically independent of increment order/parallelism. Any `--threads 1` vs `--threads N` divergence is therefore DEFINITIVELY a concurrency bug (lost update / double count) — never benign ordering. This makes the differential test high-signal, zero-noise.

---

## Per-Task Verification Map

> Task IDs finalized when PLAN.md files are written. Mapped at the plan/requirement level here; the planner lifts each into `<automated>` verify blocks.

| Plan | Wave | Requirement | Test Type | Automated Command | Status |
|------|------|-------------|-----------|-------------------|--------|
| 02-01 (thread plumbing) | 1 | PCOUNT-01 | unit + integration | `cargo test --test parallel_count_tests -- test_thread_resolution` | ⬜ pending |
| 02-02 (dashmap + par_iter) | 2 | PCOUNT-02 | unit (inline) | `cargo test --lib hash::table::tests` | ⬜ pending |
| 02-03 (PyCounter GIL release) | 2 | PCOUNT-03 | integration (pytest) | `pytest pyo3/tests/test_counter.py` | ⬜ pending |
| 02-04 (differential correctness) | 2 | PCOUNT-04 | integration (differential) | `cargo test --test parallel_count_tests -- differential` | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/parallel_count_tests.rs` — NEW differential test binary (covers PCOUNT-01, PCOUNT-04, default-sort determinism). Reuses `tests/common/mod.rs` factories + `tests/fixtures/`.
- [ ] `tests/fixtures/parallel_count_baseline/` — pre-refactor count MAPS (JSON, not bytes) captured golden-capture-first (D-10). One per D-13 cell. **Captured BEFORE the dashmap swap (first task of plan 02-04).**
- [ ] `pyo3/tests/test_counter.py` — extend with `threads` kwarg + GIL-release parallel case (PCOUNT-03). Guard with `try: import pyrustkmer`.
- [ ] Extend `src/hash/table.rs` inline tests: `test_increment_atomic_under_concurrency` (N threads increment same k-mer → count == N) + `test_overflow_preserved` (increment to u32::MAX, next errors).

*Framework install: none — `cargo test`, `proptest`, `pytest` all present.*

---

## Manual-Only Verifications

*All phase behaviors have automated verification.* (Speedup/scaling magnitude itself is measured by the Phase 4 benchmark harness, not a manual check — out of Phase 2 scope.)

---

## Validation Sign-Off

- [x] All tasks will have `<automated>` verify or Wave 0 dependencies (planner enforces)
- [x] Sampling continuity: no 3 consecutive tasks without automated verify (differential subset runs per task)
- [x] Wave 0 covers all MISSING references (4 new/extended test artifacts above)
- [x] No watch-mode flags
- [x] Feedback latency < 20s (quick subset)
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending (set to `approved YYYY-MM-DD` after planner emits `<automated>` blocks)
