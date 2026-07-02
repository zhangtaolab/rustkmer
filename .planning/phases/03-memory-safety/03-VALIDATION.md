---
phase: 3
slug: memory-safety
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-07-02
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Sourced from `03-RESEARCH.md` §"Validation Architecture". The planner lifts Dimension 8 (validation requirements) from this file and the per-task map is completed as PLAN.md task IDs are assigned.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | `cargo test` (built-in) + `proptest 1.5` (Rust property tests); `pytest >=7.0` (Python contract tests for pyrustkmer) |
| **Config file** | Root: none (cargo defaults). pyo3: `pyo3/pyproject.toml` `[tool.pytest.ini_options]` (coverage gate `--cov-fail-under=80`) |
| **Quick run command** | `cargo test --lib` |
| **Full suite command** | `cargo test --all && cargo test --test parallel_count_tests && (cd pyo3 && maturin develop --release && pytest)` |
| **Estimated runtime** | ~60–120 seconds (Rust lib + integration + pyo3 wheel build + pytest) |

---

## Sampling Rate

- **After every task commit:** Run `cargo test --lib`
- **After every plan wave:** Run `cargo test --all && cargo test --test parallel_count_tests && cargo test --test dense_differential_tests && cargo test --test merge_cleanup_tests`
- **Before `/gsd-verify-work`:** Full Rust suite + `pyo3` Python suite green; `cargo clippy --all-targets -- -D warnings` clean on BOTH root crate and `pyo3/` (Phase 1 FOUND-01 gate)
- **Max feedback latency:** ~120 seconds

---

## Per-Requirement Verification Map

> Task IDs are filled in by the planner as PLAN.md tasks are assigned. Each requirement maps to at least one automated test (no manual-only verification for Phase 3's behaviors).

| Req ID | Behavior | Test Type | Automated Command | Test File | Status |
|--------|----------|-----------|-------------------|-----------|--------|
| MERGE-01 | Merge defaults to streaming; oversized estimate routes to streaming, not in-memory | unit + integration | `cargo test --test merge_routing_tests` | ❌ Wave 0 `tests/merge_routing_tests.rs` | ⬜ pending |
| MERGE-02 | Admission control: estimate > budget hard-routes to streaming; header-only read (NO entry materialization) | unit | `cargo test --lib should_use_streaming_header_only` + `cargo test --lib estimator_does_not_materialize_entries` | ❌ Wave 0 inline `src/database/format.rs #[cfg(test)]` | ⬜ pending |
| MERGE-03 | Failed/interrupted streaming merge cleans up temp shards (RAII + process-unique subdir + startup sweep) | integration | `cargo test --test merge_cleanup_tests` (panic-injection leaves no shards; orphan subdir swept on next start; concurrent merges isolated) | ❌ Wave 0 `tests/merge_cleanup_tests.rs` | ⬜ pending |
| MERGE-04 | `PyDatabase.merge` threads `max_memory`/`merge_mode` kwargs through to the bounded core | Python contract | `(cd pyo3 && maturin develop --release && pytest tests/test_database_merge.py -k bounded_merge)` | ❌ Wave 0 `pyo3/tests/test_database_merge.py` | ⬜ pending |
| DENSE-01 | k ≤ 32 counter uses u64 internally; `memory_usage()` reflects ~50% reduction vs u128 | unit + benchmark | `cargo test --lib dense_counter_memory` (assert k=21 `memory_usage()` ≈ half of equivalent u128 counter, within hash-overhead tolerance) | ❌ Wave 0 inline `src/hash/table.rs #[cfg(test)]` | ⬜ pending |
| DENSE-02 | `.rkdb` v2 byte-identity preserved post-dense; golden sha256 baselines unchanged | integration (golden re-verification) | `cargo test --test golden_sha256_tests` (re-hash 12 `tests/fixtures/golden_k*.rkdb`, compare to `golden_manifest.sha256`) | ❌ Wave 0 `tests/golden_sha256_tests.rs` (reuses existing fixtures — NO new baseline capture) | ⬜ pending |
| DENSE-03 | u64 path canonicalization + counts == u128 path (decoded-level differential, D-04/D-05) | integration + property | `cargo test --test dense_differential_tests` (D-13 matrix k ∈ {21,32,64} × canon × sorted, decoded-map equality) + `cargo test --test dense_proptest` (random small inputs) | ❌ Wave 0 `tests/dense_differential_tests.rs`, `tests/dense_proptest.rs` | ⬜ pending |

### Per-Task Verification Map

*(Filled in by the planner — each PLAN.md task gets a row citing its Req ID + the automated command above. Every task MUST have an `<automated>` verify or a Wave 0 dependency.)*

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| _TBD (planner fills)_ | — | — | — | — | — | — | — | — | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/merge_routing_tests.rs` — covers MERGE-01, MERGE-02 (estimator header-only fix + hard-route)
- [ ] `tests/merge_cleanup_tests.rs` — covers MERGE-03 (RAII + process-unique subdir + startup sweep + panic-injection)
- [ ] `tests/dense_differential_tests.rs` — covers DENSE-03 (u64-vs-u128 decoded differential, D-13 matrix)
- [ ] `tests/dense_proptest.rs` — covers DENSE-03 (proptest on random small inputs)
- [ ] `tests/golden_sha256_tests.rs` — covers DENSE-02 (re-verify 12 golden `.rkdb` sha256 unchanged post-dense)
- [ ] `pyo3/tests/test_database_merge.py` — covers MERGE-04 (PyDatabase.merge kwargs contract)
- [ ] Inline `#[cfg(test)]` in `src/hash/table.rs` — covers DENSE-01 (`memory_usage()` ~50% reduction assertion)
- [ ] Inline `#[cfg(test)]` in `src/database/format.rs` — covers MERGE-02 (estimator header-only + no-materialization)

*Framework check: `cargo test` already configured; `proptest 1.5` already a dev-dep; `pytest` configured in `pyo3/pyproject.toml`. No new framework install needed.*

*Existing infrastructure covers the carry-forward Phase 1/2 tests — `tests/parallel_count_tests.rs` must stay green (dense swap must not regress PCOUNT-04).*

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

> Note: the actual human-scale no-OOM behavior on CRR1936095 is validated in **Phase 4** (benchmark harness). Phase 3 proves the routing/cleanup/correctness **logic** on synthetic inputs at toy scale — the estimator is `total_kmers × 24 > budget`, independent of absolute size, so a tiny-budget toy merge exercises the same no-OOM path. See `03-RESEARCH.md` §"How to PROVE MERGE-01 (no-OOM) and DENSE-03 (canonicalization correctness) without a human-scale dataset in CI".

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (the 8 test files above)
- [ ] No watch-mode flags
- [ ] Feedback latency < 120s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
