---
phase: "13"
slug: "producer-attribution-research"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-11-17"
---

# Phase 13 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Python stdlib `unittest` (harness suite; no pytest/conftest by contract) |
| **Config file** | none — discover-based (`python3 -m unittest discover -s scripts/bench/tests -t .`) |
| **Quick run command** | `python3 -m unittest scripts.bench.tests.test_phase13_driver -v` (new module) |
| **Full suite command** | `python3 -m unittest discover -s scripts/bench/tests -t .` (~717+ tests, plus `cargo test` unaffected — no Rust changes) |
| **Estimated runtime** | ~15 seconds (full suite) |

---

## Sampling Rate

- **After every task commit:** Run the new-driver unit module (fast, fixture-only)
- **After every plan wave:** Run the full harness unittest suite
- **Before `/gsd-verify-work`:** Full-scale session green (all fail-loud gates passed) + memo committed; fixture-scale rehearsal green BEFORE the full-scale session (rehearsal numbers never feed the gate)
- **Max feedback latency:** ~15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| (planner pins) | TBD | 0 | PEXT-01 | TBD | fingerprint gate branches: match → cite, mismatch → refuse non-fresh base | unit (fixture sha256s) | `python3 -m unittest scripts.bench.tests.test_phase13_driver -v` | ❌ W0 | ⬜ pending |
| (planner pins) | TBD | 0 | PEXT-01 | TBD | attribution arithmetic (δ correction, stage residuals, composition split) on fixture numbers | unit (pure functions) | same | ❌ W0 | ⬜ pending |
| (planner pins) | TBD | 0 | PEXT-01 | TBD | evidence schema: full-scale-only enforcement + provenance completeness | unit | same | ❌ W0 | ⬜ pending |
| (planner pins) | TBD | 0 | PEXT-01 | TBD | fail-loud parsing: probe JSON missing k / malformed → loud abort | unit | same | ❌ W0 | ⬜ pending |
| (planner pins) | TBD | 0 | PEXT-02 | TBD | predicted-win model: both ceilings present, every input resolved to a named run or loud failure | unit | same | ❌ W0 | ⬜ pending |
| (planner pins) | TBD | 1+ | PEXT-01/02 | — | end-to-end driver rehearsal on tiny fixtures (arms A-D + control, gates green) at fixture scale | integration (driver --rehearsal) | driver invocation in plan verify | ❌ W0 | ⬜ pending |
| (session) | TBD | — | PEXT-01 | — | full-scale measurement session + gates | measurement (the deliverable) | driver --run (~1.5-2 h) | ❌ in-phase | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `scripts/bench/tests/test_phase13_driver.py` — fingerprint gate, attribution math, schema/full-scale guards, fail-loud parsing, model completeness (covers PEXT-01/02 unit layer)
- [ ] Driver `--rehearsal` fixture-scale mode — proves materialization → run → evidence → memo-derivation chain end-to-end without full-scale cost
- [ ] Known-flake note: `scripts/bench/tests/test_verify_threads.py::TestNegativeControls::test_pre_engine_n_plus_one_stub_is_measured_red` — pre-existing ~50% macOS `sample`-race flake (STATE.md); purge stale `target/` before trusting a red

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Full-scale attribution session (arms A-D × 2 k × 3 reps) with gates green | PEXT-01 | Live ~1.5-2 h measurement on real data — the deliverable itself | Run the driver --run; verify all fail-loud gates green, evidence JSON schema-valid, memo derivation consumes only full-scale records |
| D3 go/no-go memo derivation from cited numbers | PEXT-02 | Judgment recorded as evidence, not a unit test | Review 13-GATE-MEMO.md: both ceilings named, every input cited to a named full-scale run record, decision consistent with the pre-registered bar |

*All other phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
