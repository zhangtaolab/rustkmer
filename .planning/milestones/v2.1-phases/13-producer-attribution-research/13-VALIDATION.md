---
phase: "13"
slug: "producer-attribution-research"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: validated
nyquist_compliant: true
wave_0_complete: true
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
| **Quick run command** | `python3 -m unittest scripts.bench.tests.test_phase13_driver -v` (80 tests) |
| **Full suite command** | `python3 -m unittest discover -s scripts/bench/tests -t .` (797 tests, 1 skipped [VERIFIED 2026-11-17]; plus `cargo test` unaffected — no Rust changes) |
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
| 13-01-T1 | 13-01 | 0 | PEXT-01/02 | T-13-01 | driver skeleton + fixture-scale rehearsal chain proof (all arms/control, zero-entry guards) | unit + integration (`--rehearsal`) | `python3 -m unittest scripts.bench.tests.test_phase13_driver -v`; `python3 scripts/bench/phase13.py --rehearsal` | ✅ | ✅ green |
| 13-01-T2 | 13-01 | 0 | PEXT-01/02 | T-13-02 | prep/measure/memo stages; probe materialization + committed-lock sha256 gate; fail-loud probe parsing | unit (fixture-only) | same module | ✅ | ✅ green |
| 13-01-T3 | 13-01 | 0 | PEXT-01/02 | T-13-03 | attribution arithmetic, two-ceiling predicted win, D-05 decision, memo branch coverage | unit (pure functions) | same module (80 tests) | ✅ | ✅ green |
| 13-02-T1 | 13-02 | 1 | PEXT-01 | T-13-04 | fingerprint gate takes the `re-measure` branch; six plain-part sha256+size provenance; disk arithmetic | measurement (live prep stage) | plan verify blocks: provenance/disk/sha256 assertions | ✅ | ✅ green |
| 13-02-T2 | 13-02 | 2 | PEXT-01/02 | T-13-05, T-13-06 | complete full-scale matrix + provenance at both k; D-09 attribution; D-05 decision | measurement + automated evidence checks | plan verify blocks: `matrix-ok`, `context-and-probe-ok`, `tree-clean`, `evidence-committed` | ✅ | ✅ green |
| 13-03-T1 | 13-03 | 3 | PEXT-02 | T-13-08, T-13-09 | deterministic memo render + byte-identical re-render proof + scoped ROADMAP annotation | unit + render proof | `python3 scripts/bench/phase13.py --stage memo`; `proof-ok`, `memo-sections-ok`, `roadmap-annotated`, `memo-committed` | ✅ | ✅ green |
| 13-03-T2 | 13-03 | 3 | PEXT-02 | T-13-07 | deletion only after memo commit; provenance survives in evidence; gzip root untouched | automated lifecycle checks | `plain-count=0`, `probe-scratch-gone`, `gzip-part-count=6`, `lifecycle-ok`, `wrapup-committed` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `scripts/bench/tests/test_phase13_driver.py` — fingerprint gate, attribution math, schema/full-scale guards, fail-loud parsing, model completeness (covers PEXT-01/02 unit layer; 80 tests green)
- [x] Driver `--rehearsal` fixture-scale mode — proves materialization → run → evidence → memo-derivation chain end-to-end without full-scale cost
- [x] Known-flake note: `scripts/bench/tests/test_verify_threads.py::TestNegativeControls::test_pre_engine_n_plus_one_stub_is_measured_red` — pre-existing ~50% macOS `sample`-race flake (STATE.md); purge stale `target/` before trusting a red

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Full-scale attribution session (arms A-D × 2 k × 3 reps) with gates green | PEXT-01 | Live 2 h 19 min measurement on real data — the deliverable itself | EXECUTED 2026-11-17: 60 full-scale gate records + 16 excluded context records in `13-ATTRIBUTION.json`; all fail-loud gates green; `git_dirty: false` on the rebuilt binary |
| D3 go/no-go memo derivation from cited numbers | PEXT-02 | Judgment recorded as evidence, not a unit test | `13-GATE-MEMO.md` committed with byte-identical re-render proof; both ceilings named, every input cited, decision NO-GO consistent with the pre-registered 10.0 bar at both k |

*All other phase behaviors have automated verification.*

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 60s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** validated 2026-11-17 (automated audit; 0 gaps found)

## Validation Audit 2026-11-17

| Metric | Count |
|---|---|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |
