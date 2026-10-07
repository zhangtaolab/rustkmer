---
phase: 3
slug: memory-safety
status: validated
nyquist_compliant: false
wave_0_complete: true
created: 2026-07-02
validated: 2026-10-07
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Sourced from `03-RESEARCH.md` §"Validation Architecture".
>
> **Status note (2026-10-07):** this file was seeded at *planning* time and has now been
> **audited post-execution** against the shipped implementation. The Test Infrastructure,
> Sampling Rate, and bounding-proof strategy below were verified accurate and are retained
> as-is. The Per-Requirement map, Per-Task map, and Sign-Off are updated with measured results.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | `cargo test` (built-in) + `proptest 1.5` (Rust property tests); `pytest >=7.0` (Python contract tests for pyrustkmer) |
| **Config file** | Root: none (cargo defaults). pyo3: `pyo3/pyproject.toml` `[tool.pytest.ini_options]` (coverage gate `--cov-fail-under=80`) |
| **Quick run command** | `cargo test --lib` |
| **Full suite command** | `cargo test --all && cargo test --test parallel_count_tests && (cd pyo3 && maturin develop --release && pytest)` |
| **Estimated runtime** | ~60–120 seconds (Rust lib + integration + pyo3 wheel build + pytest) |

**Verified 2026-10-07.** `cargo test` exits 0 (221 lib tests + all integration binaries, 0 failed).
`cargo clippy --all-targets -- -D warnings` is clean on **both** the root crate and `pyo3/`.

> ⚠️ **Two pre-existing pyo3 defects make the documented full-suite command unrunnable as written**
> (both are 03-05 Deviations 2 and 4, logged in `deferred-items.md` + `.planning/WINDOWS.md`, and
> neither is caused by Phase 3):
> 1. `pyo3/pyproject.toml` sets `python-source = "."`, but `pyo3/pyrustkmer/` has never existed —
>    `maturin develop` / `maturin build` both exit 1.
> 2. `addopts` forces `--cov=pyrustkmer --cov-fail-under=80`, which can never pass for a compiled
>    extension (coverage is structurally 0%), so every `pytest` invocation exits 1.
>
> **Working MERGE-04 command as of this audit:**
> `~/.cache/rustkmer-venv/bin/python -m pytest tests/test_database_merge.py -o addopts="" -q`
> → **11 passed, 0 skipped**.

---

## Sampling Rate

- **After every task commit:** Run `cargo test --lib`
- **After every plan wave:** Run `cargo test --all && cargo test --test parallel_count_tests && cargo test --test dense_differential_tests && cargo test --test merge_cleanup_tests`
- **Before `/gsd-verify-work`:** Full Rust suite + `pyo3` Python suite green; `cargo clippy --all-targets -- -D warnings` clean on BOTH root crate and `pyo3/` (Phase 1 FOUND-01 gate)
- **Max feedback latency:** ~120 seconds

---

## Per-Requirement Verification Map

> Every requirement maps to at least one automated test. Status is the **measured** post-execution
> result: ✅ covered / ⚠️ partial / ❌ missing.

| Req ID | Behavior | Test Type | Automated Command | Test File | Status |
|--------|----------|-----------|-------------------|-----------|--------|
| MERGE-01 | Merge defaults to streaming; oversized estimate routes to streaming, not in-memory | unit + integration | `cargo test --test merge_routing_tests` | ✅ `tests/merge_routing_tests.rs` | ✅ covered |
| MERGE-02 | Admission control: estimate > budget hard-routes to streaming; header-only read (NO entry materialization) | unit + integration | `cargo test --test merge_routing_tests`; `cargo test --test merge_routing_tests -- estimator_reads_header_only_no_materialization` | ✅ `tests/merge_routing_tests.rs` + `src/database/format.rs` unit mod `merge_admission_control` | ✅ covered |
| MERGE-03 | Failed/interrupted streaming merge cleans up temp shards (RAII + process-unique subdir + startup sweep) | integration | `cargo test --test merge_cleanup_tests` | ✅ `tests/merge_cleanup_tests.rs` (5 tests) | ✅ covered |
| MERGE-04 | `PyDatabase.merge` threads `max_memory`/`merge_mode` kwargs through to the bounded core | Python contract | `pytest tests/test_database_merge.py -o addopts=""` | ✅ `pyo3/tests/test_database_merge.py` (11 tests) | ✅ covered |
| DENSE-01 | k ≤ 32 counter uses u64 internally; `memory_usage()` reflects ~50% reduction vs u128 | unit + integration | `cargo test --lib dense_counter_memory` | ⚠️ `src/hash/table.rs` `dense_counter_memory_usage_halved_for_k21` + `tests/dense_differential_tests.rs` | ⚠️ **PARTIAL — assertion is self-fulfilling; see BLOCKER-1 below** |
| DENSE-02 | `.rkdb` v2 byte-identity preserved post-dense; golden sha256 baselines unchanged | integration (golden re-verification) | `cargo test --test golden_sha256_tests` | ✅ `tests/golden_sha256_tests.rs` (12 fixtures re-hashed) + `tests/dense_merge_integration_tests.rs::dense_merge_output_preserves_rkdb_v2_layout` | ✅ covered |
| DENSE-03 | u64 path canonicalization + counts == u128 path (decoded-level differential, D-04/D-05) | integration + property | `cargo test --test dense_differential_tests`; `cargo test --test dense_proptest_tests` | ✅ `tests/dense_differential_tests.rs` (6) + `tests/dense_proptest_tests.rs` (3) | ✅ covered |

### Measured Results (2026-10-07)

| Suite | Result |
|-------|--------|
| `cargo test` (full) | **exit 0** — 221 lib + all integration binaries, 0 failed |
| `cargo test --test merge_routing_tests` | 26 passed, 0 failed, **0 ignored** |
| `cargo test --test merge_cleanup_tests` | 26 passed, 0 failed, **0 ignored** |
| `cargo test --test dense_differential_tests` | 6 passed, 0 failed, 0 ignored |
| `cargo test --test dense_proptest_tests` | 3 passed, 0 failed, 0 ignored |
| `cargo test --test golden_sha256_tests` | 2 passed, 0 failed, 0 ignored |
| `cargo test --test dense_merge_integration_tests` | 3 passed, 0 failed, 0 ignored |
| `cargo test --lib dense_counter_memory` | 1 passed (`dense_counter_memory_usage_halved_for_k21`) |
| `pytest tests/test_database_merge.py -o addopts=""` | **11 passed, 0 skipped** |
| `cargo clippy --all-targets -- -D warnings` (root + `pyo3`) | **clean** |

**Zero `#[ignore]` attributes remain** in any Phase 3 test file (verified via
`grep -rnE '^\s*#\s*\[\s*ignore' tests/{merge_routing,merge_cleanup,dense_differential,dense_proptest,golden_sha256,dense_merge_integration}_tests.rs` → no matches).
This closes the 03-04 deferred item that flagged 3 prose-level grep hits.

### Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 03-01-01 | 01 | 0 | MERGE-01, MERGE-02 | T-03-01 | Wave-0 RED stubs scaffold the routing contract | integration | `cargo test --test merge_routing_tests` | ✅ | ✅ green |
| 03-01-02 | 01 | 1 | MERGE-01, MERGE-02 | T-03-01 | Header-only estimator; hard-route; D-02 reject branch | unit + integration | `cargo test --test merge_routing_tests` | ✅ | ✅ green |
| 03-02-01 | 02 | 0 | MERGE-03 | T-03-05 | Wave-0 RED stubs for temp lifecycle | integration | `cargo test --test merge_cleanup_tests` | ✅ | ✅ green |
| 03-02-02 | 02 | 1 | MERGE-03 | T-03-05, T-03-06 | RAII on prefix-cache path + process-unique subdir + startup sweep | integration | `cargo test --test merge_cleanup_tests` | ✅ | ✅ green |
| 03-03-01 | 03 | 0 | DENSE-01/02/03 | T-03-10, T-03-11 | Wave-0 RED stubs: `KmerKey` + 3 test binaries | integration | `cargo test --test dense_differential_tests` | ✅ | ✅ green |
| 03-03-02 | 03 | 1 | DENSE-01/02/03 | T-03-10, T-03-11 | `DashMap<KmerKey, u32>` swap; width-aware `increment`/`memory_usage`/`get_all_counts` | unit + integration | `cargo test --lib dense_counter_memory`; `cargo test --test golden_sha256_tests` | ✅ | ⚠️ **DENSE-01 assertion vacuous — BLOCKER-1** |
| 03-04-01 | 04 | 2 | MERGE-01, MERGE-02, DENSE-02, DENSE-03 | T-03-13 | Cross-plan composition: u64 count → `.rkdb` → bounded merge → decode, 4-way equality on **both** routes | integration | `cargo test --test dense_merge_integration_tests` | ✅ | ✅ green |
| 03-05-01 | 05 | 0 | MERGE-04 | — | Wave-0 RED stubs for the Python merge contract | Python | `pytest tests/test_database_merge.py` | ✅ | ✅ green |
| 03-05-02 | 05 | 1 | MERGE-04 | T-03-17 | `max_memory`/`merge_mode` kwargs threaded into `MergeConfig` | Python | `pytest tests/test_database_merge.py -o addopts=""` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ partial/flaky*

---

## Wave 0 Requirements

- [x] `tests/merge_routing_tests.rs` — covers MERGE-01, MERGE-02 (estimator header-only fix + hard-route) — **6 tests green**
- [x] `tests/merge_cleanup_tests.rs` — covers MERGE-03 (RAII + process-unique subdir + startup sweep + panic-injection) — **5 tests green**
- [x] `tests/dense_differential_tests.rs` — covers DENSE-03 (u64-vs-u128 decoded differential, D-13 matrix) — **6 tests green**
- [x] `tests/dense_proptest_tests.rs` — covers DENSE-03 (proptest on random small inputs) — **3 tests green**
- [x] `tests/golden_sha256_tests.rs` — covers DENSE-02 (re-verify 12 golden `.rkdb` sha256 unchanged post-dense) — **2 tests green**
- [x] `pyo3/tests/test_database_merge.py` — covers MERGE-04 (PyDatabase.merge kwargs contract) — **11 tests green, 0 skipped**
- [x] Inline `#[cfg(test)]` in `src/hash/table.rs` — covers DENSE-01 — **1 test green but VACUOUS, see BLOCKER-1**
- [x] `tests/dense_merge_integration_tests.rs` — *(added by 03-04, beyond the Wave 0 list)* cross-plan composition gate — **3 tests green**

*Framework check: `cargo test` already configured; `proptest 1.5` already a dev-dep; `pytest` configured in `pyo3/pyproject.toml`. No new framework install needed.*

*Existing infrastructure covers the carry-forward Phase 1/2 tests — `tests/parallel_count_tests.rs` stays green (dense swap did not regress PCOUNT-04).*

---

## Manual-Only Verifications

*Not everything in this phase has a sound automated check. Two items below are recorded here
because they are either measurement-limited or blocked on an implementation defect.*

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Real per-entry memory cost of the dense counter | DENSE-01 | `memory_usage()` is a **model** (24 B overhead + key + 4 B), not a measurement. Deferred from 03-03; Phase 4's benchmark harness is the right place. See `deferred-items.md`. | Measure a heap delta or allocator stats for k=21 vs k=64 at equal entry counts. |
| **DENSE-01 storage-width claim** | DENSE-01 | **BLOCKER-1** — the automated assertion cannot fail for the reason it claims. Escalated to developer; not fixable by a test. | See BLOCKER-1 below. |

> Note: the actual human-scale no-OOM behavior on CRR1936095 is validated in **Phase 4** (benchmark
> harness). Phase 3 proves the routing/cleanup/correctness **logic** on synthetic inputs at toy scale —
> the estimator is `total_kmers × 24 > budget`, independent of absolute size, so a tiny-budget toy merge
> exercises the same no-OOM path. See `03-RESEARCH.md` §"How to PROVE MERGE-01 (no-OOM) and DENSE-03
> (canonicalization correctness) without a human-scale dataset in CI".

---

## BLOCKER-1 — DENSE-01's storage-width assertion is vacuous (ESCALATED)

**Severity:** BLOCKER — a requirement reported as verified that no test can actually falsify.
**Owner:** developer (implementation defect — NOT fixable by writing a test).

### The claim under audit

`src/hash/table.rs:1018` — `dense_counter_memory_usage_halved_for_k21` asserts that a k=21 counter
models 8-byte keys and a k=64 counter models 16-byte keys, concluding that DENSE-01 ("k ≤ 32 stored
as `u64` instead of `u128`, roughly halving counting memory") is satisfied.

`tests/dense_differential_tests.rs:237` and `:247` make the same assertion, and their doc comments
state that `memory_usage()` is *"a direct observation of which `KmerKey` variant the counter selected"*.
`tests/dense_merge_integration_tests.rs:457` repeats it with the same reasoning.

### Why it is vacuous

`memory_usage()` computes its width from **`kmer_length`, not from the stored key**:

- `src/hash/table.rs:352` — `pub fn memory_usage(&self) -> usize { self.table.len() * (HASH_OVERHEAD_PER_ENTRY + self.key_bytes() + COUNT_BYTES) }`
- `src/hash/table.rs:361` — `fn key_bytes(&self) -> usize { if self.kmer_length <= MAX_KMER_SIZE_IN_U64 { U64_KEY_BYTES } else { U128_KEY_BYTES } }`

`key_bytes()` never inspects a `KmerKey` value, and no test in the phase does either — there is no
`size_of::<KmerKey>()` assertion, no variant accessor, and `KmerKey` is not introspectable from
outside `src/hash/`. **The mutation "always store `KmerKey::U128`" would leave all three assertions
green**, because the reported number is a pure function of `k`. The test restates the branch
condition; it does not observe the branch being taken.

### The underlying defect this hid

`KmerKey` is an enum with a `u128` variant, so Rust gives it `u128`'s 16-byte alignment and rounds
the total up to **32 bytes**. Measured with a standalone probe replicating the exact declaration
(`#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)] pub enum KmerKey { U64(u64), U128(u128) }`):

```
size_of::<KmerKey>()  = 32 bytes
size_of::<u128>()     = 16 bytes   (pre-Phase-3 DashMap key)
dense key + u32 count = 32 + 4 = 36 bytes   ratio vs legacy 1.80
model claims          =  8 + 4 = 12 bytes   ratio vs legacy 0.60
```

So for a k=21 counter — the exact case DENSE-01 is about — the real per-entry key+value footprint is
**36 bytes versus the pre-Phase-3 20 bytes**. The plan's own rationale ("the discriminant never adds
live storage cost", `src/hash/key.rs:31-34`) does not hold: the discriminant *is* paid on every entry,
because the enum's layout is fixed at compile time and the `U128` variant forces the alignment.
DENSE-01 as implemented **increases** counting memory rather than halving it.

This compounds a defect already recorded in `deferred-items.md`: that entry scopes the problem to the
width-independent 24 B modelled overhead. The enum padding is a separate and larger effect — it is in
the key itself and makes the modelled 8 B an overstatement by 4×, not an understatement of the saving.

### Scope check — is DENSE-03 affected?

No. `KmerKey::to_u128` is a lossless zero-extension on the `U64` path, and the decoded-level
differential in `tests/dense_differential_tests.rs` (6 tests) plus the proptest (3 tests) compare
**decoded `(String, u32)` maps**, which is the correct D-04 discipline. Those tests are sound and
green. The defect is confined to the *memory* claim (DENSE-01), not the *correctness* claim (DENSE-03),
and it does not affect DENSE-02 (on-disk `.rkdb` v2 bytes are untouched — golden sha256 still match).

### Suggested fix (for the developer — NOT applied here)

Give the dense width its own monomorphized table so the key type has no `u128` in it, e.g.
`KmerCounter<K>` over `u64`/`u128`, or two concrete counter types selected at `KmerCounter::new`.
The plan considered and rejected this ("Pattern 1, Option A") on blast-radius grounds; that trade-off
should be re-opened, because the enum silently costs more than the `u128` it replaced. Any fix must
keep `get_all_counts() -> Vec<(u128, u32)>` unchanged so DENSE-02 and the pyo3/count.rs call sites
still compile (Phase 2 D-05 carry-forward).

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies — 9/9 tasks
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references — all 8 planned files exist and run green
- [x] No watch-mode flags
- [x] Feedback latency < 120s (full `cargo test` measured well under)
- [ ] `nyquist_compliant: true` set in frontmatter — **NOT set**: BLOCKER-1 is open

**Coverage summary:** 6 of 7 requirements fully covered (MERGE-01, MERGE-02, MERGE-03, MERGE-04,
DENSE-02, DENSE-03). **DENSE-01 is PARTIAL** — its correctness consequences are covered transitively
by DENSE-03, but its central storage-width claim is asserted by a test that cannot fail (BLOCKER-1).

**Non-vacuity audit result.** The vacuity class the phase's own executors twice caught (a routing test
that passes with the routing removed) was re-checked here requirement-by-requirement and **no
remaining instance was found**. Specifically:

- `tests/merge_routing_tests.rs` proves route selection with a behavioral probe — `temp_dir` pointed
  at a **nonexistent** directory, where the streaming path must fail creating a chunk file
  (`Err`) and the in-memory path never touches `temp_dir` (`Ok`). Removing the routing flips these
  outcomes, so `merge_over_budget_hard_routes_to_streaming` (`:279`), `merge_explicit_streaming_mode_always_streams`
  (`:349`) and the in-memory control at `:233` all genuinely discriminate.
- `tests/dense_merge_integration_tests.rs` derives its budget from the real
  `RKDatabase::estimate_total_kmers` (`:422-437`) instead of hard-coding `1024`, and asserts the route
  with `assert_route` before every streaming claim (`:507, :515, :521, :615, :776, :828`). The module
  docstring records that the hard-coded budget made an earlier draft vacuous.
- `pyo3/tests/test_database_merge.py` reproduces the core's estimate model in `_estimated_bytes` (`:114`)
  and derives its budget from it (`:129`), with a `TMPDIR` redirect proving the streaming route by the
  chunk-file error message (`:315`).
- `tests/merge_cleanup_tests.rs` constructs `ExternalSortMerger` — which is defined in
  `src/database/prefix_cache_merge.rs`, the path that actually leaked — so MERGE-03 is tested against
  the defective path, not a stand-in.

**Approval:** validated 2026-10-07 — **PARTIAL** (1 requirement blocked; 6 requirements verified)

## Validation Audit

| Field | Value |
|-------|-------|
| Gaps found | 1 |
| Resolved | 0 |
| Escalated | 1 |