---
phase: 1
slug: foundation-quality
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-07-01
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Derived from `01-RESEARCH.md` § Validation Architecture. The planner refines the Per-Task map once PLAN.md task IDs exist.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Rust built-in `cargo test` harness + `syn` 2.x (dev-dep) for the CJK scan; `pytest` 7.x for pyo3 binding smoke |
| **Config file** | `Cargo.toml` (root), `pyo3/pyproject.toml` (pytest); no `rustfmt.toml`/`clippy.toml` (default lint settings) |
| **Quick run command** | `cargo test --lib` (root unit/inline tests) |
| **Full suite command** | `cargo test` (root) + `cd pyo3 && cargo test` (pyo3 binding smoke) |
| **Clippy gate command** | `cargo clippy --all-targets -- -D warnings` (root) + `cd pyo3 && cargo clippy --all-targets -- -D warnings` |
| **Estimated runtime** | ~60–120 s (root Rust suite); pyo3 smoke ~30 s |

---

## Sampling Rate

- **After every task commit:** Run `cargo test --lib` + `cargo clippy --all-targets` (catches print-lint regressions immediately)
- **After every plan wave:** Run `cargo test` (full root suite) + `cd pyo3 && cargo test` + `cd pyo3 && cargo clippy --all-targets -- -D warnings`
- **Before `/gsd-verify-work`:** Full suite green on BOTH `ubuntu-latest` AND `macos-latest` (CI matrix); `golden_tests` + `cjk_check` + `legacy_readback_tests` all pass
- **Max feedback latency:** ~120 s (local quick run)

---

## Per-Task Verification Map

> Task IDs finalized by the planner (plans `01-01`..`01-04`). Requirement-level map below; planner lifts into per-task rows.

| Task ID (plan) | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|----------------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 01-01 (CI gate) | 01-01 | 1 | FOUND-01 | T-ci-gate | workflow uses `on: pull_request` (NOT `pull_request_target`) | CI-gate (YAML) + smoke | `.github/workflows/ci.yml` runs green on a PR | ❌ W0 (new) | ⬜ pending |
| 01-01 (clippy clean) | 01-01 | 1 | FOUND-01 | — | n/a | CI-gate | `cargo clippy --all-targets -- -D warnings` (root); `cd pyo3 && cargo clippy --all-targets -- -D warnings` | ❌ W0 (fix 68+17 warnings) | ⬜ pending |
| 01-01 (wheel) | 01-01 | 1 | FOUND-01 | — | n/a | CI-gate | `cd pyo3 && maturin build` (sdist+wheel, ubuntu+macOS) | ❌ W0 (CI step) | ⬜ pending |
| 01-02 (log facade) | 01-02 | 1 | FOUND-02 | T-log-leak | no secrets logged (project has none); message text preserved | grep + clippy | `cargo clippy -- -D clippy::print_stdout,clippy::print_stderr,clippy::dbg_macro` | ❌ W0 (deny config + migrate 133 calls) | ⬜ pending |
| 01-02 (default info) | 01-02 | 1 | FOUND-02 (P2) | — | default filter stays `info` | unit (grep) | `grep 'default_filter_or("info")' src/main.rs` | ✅ (L13, assert preserved) | ⬜ pending |
| 01-02 (parallel logs) | 01-02 | 1 | FOUND-02 (edge) | — | rayon-path logging doesn't corrupt counts | integration (backstop) | `cargo test --test consistency_tests` (extend) | ❌ W0 (held-out edge) | ⬜ pending |
| 01-03 (byte-identity) | 01-03 | 2 | FOUND-03 | — | n/a | golden (sha256) | `cargo test --test golden_tests` (12 matrix cells) | ❌ W0 (new + fixtures) | ⬜ pending |
| 01-03 (round-trip) | 01-03 | 2 | FOUND-03 | — | n/a | integration | `cargo test` (extend format.rs inline OR `tests/round_trip_tests.rs`) | ✅ partial (format.rs:1138+) | ⬜ pending |
| 01-03 (legacy read) | 01-03 | 2 | FOUND-03 | — | reader surfaces incompatible files loudly (Err) | integration | `cargo test --test legacy_readback_tests` | ❌ W0 (new + fixture) | ⬜ pending |
| 01-04 (CJK check) | 01-04 | 1 | FOUND-04 | — | n/a | unit (syn-based, visit_lit + visit_macro) | `cargo test --test cjk_check` | ❌ W0 (new + syn dev-dep) | ⬜ pending |
| 01-04 (no deletion) | 01-04 | 1 | FOUND-04 (P4) | — | messages translated, not emptied | judgment (review-time) | manual review | n/a | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `.github/workflows/ci.yml` — covers FOUND-01 (CI gate file)
- [ ] Fix 68 root-crate + 17 pyo3 clippy warnings — prerequisite for `-D warnings` green (FOUND-01)
- [ ] `src/lib.rs` + `src/cli/mod.rs` + `pyo3/src/lib.rs` deny/allow attributes — covers FOUND-02 (clippy gate config)
- [ ] `tests/cjk_check.rs` + `syn` (+ `proc-macro2`) dev-dep — covers FOUND-04
- [ ] `tests/fixtures/golden_*.rkdb` (12 files) + `tests/golden_tests.rs` — covers FOUND-03 (byte-identity); **capture BEFORE count.rs refactor (D-10)**
- [ ] `tests/fixtures/legacy_v2_offset42.rkdb` + `tests/legacy_readback_tests.rs` — covers FOUND-03 (legacy read)
- [ ] Round-trip test extension (`src/database/format.rs` inline OR `tests/round_trip_tests.rs`) — covers FOUND-03 (round-trip)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| CI matrix actually runs green on a real PR on both ubuntu + macOS | FOUND-01 | GH Actions only fires on push/PR event; cannot fully assert locally | Open a PR; confirm both matrix jobs go green; confirm a deliberate `println!` in `src/lib.rs` fails the clippy job |
| Former CJK literals have equivalent English meaning (not emptied) | FOUND-04 (P4) | Semantic equivalence is a judgment call | Review each migrated message in `prefix_cache_merge.rs` + `pyo3/src/` for faithful English |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 120 s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
