---
phase: "12"
slug: "full-scale-merge-verdict"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: validated
nyquist_compliant: true
wave_0_complete: true
created: "2026-11-17"
---

# Phase 12 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (host `.venv313`; Python 3.13.11) over `scripts/bench/tests/` — 644 tests collected [VERIFIED 2026-11-17] |
| **Config file** | none — bench tests run on pytest defaults; `pyo3/pyproject.toml` pytest config does not govern `scripts/bench` |
| **Quick run command** | `.venv313/bin/python -m pytest scripts/bench/tests/test_phase11_verdict.py scripts/bench/tests/test_merge_arms.py -q` |
| **Full suite command** | `.venv313/bin/python -m pytest scripts/bench/tests/ -q` (CI equivalent: `python3 -m unittest discover -s scripts/bench/tests -t .`) |
| **Estimated runtime** | ~15 seconds (full suite, 644 tests) |

---

## Sampling Rate

- **After every task commit:** Run the quick run command (controller/renderer tests + merge-arm tests)
- **After every plan wave:** Run the full suite command
- **Before `/gsd-verify-work`:** Full suite green + session gates green + exit-code record + re-render proof
- **Max feedback latency:** ~15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 12-01 T1 | 12-01 | 1 | MBENCH-03/04 | T-12-01..03 | controller 0/1/2 contract; renderer no-literals; verdict/doc layouts | unit | `.venv313/bin/python -m pytest scripts/bench/tests/test_phase11_verdict.py -q` | ✅ | ✅ green |
| 12-04 T1 | 12-04 | 2 | MBENCH-03 | T-12-04..05 | round-0 revalidate gate fails loud; anchors exact; D-12 budget via check_disk_floor | unit (fixtures) + in-stage verb | pytest test_phase11_verdict.py + `prepare_inputs.py revalidate` in-stage | ✅ | ✅ green |
| 12-04 T1 | 12-04 | 2 | MBENCH-03 | — | counterbalanced schedule shape (3 arms × 3 reps, rotated starts) | unit | schedule-shape tests over `rotation_schedule` | ✅ | ✅ green |
| 12-04 T1 | 12-04 | 2 | MBENCH-03 | — | parity legs green before results acceptance; Leg-2 recount diff raises on first mismatch | unit (fixture dumps) + live both-k evidence | pytest test_phase11_verdict.py (streaming pipeline fixtures) | ✅ | ✅ green |
| 12-01 T1 | 12-01 | 1 | MBENCH-04 | — | renderer: no measurement literals; entry-rate/byte-rate formulas; asymmetry sentence; predicted-vs-measured caveat | unit | pytest test_phase11_verdict.py (renderer tests) | ✅ | ✅ green |
| 12-01 T1 | 12-01 | 1 | MBENCH-04 | — | byte-identical re-render proof | unit (render twice, byte-compare) + live proof 12-RENDER-PROOF.json | renderer test + committed proof | ✅ | ✅ green |
| 12-02 (session) | 12-02 | 3 | MBENCH-03 | — | full-scale session itself | session evidence | staged runs; gates green + schema-valid results + recorded exit code 0 | n/a — the deliverable | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `scripts/bench/tests/test_phase11_verdict.py` — controller contract (73 tests green: stages, exit codes, schedule shape, Leg-2 recount fixtures, renderer byte-identity + metric formulas); covers the MBENCH-03/04 unit surface
- [x] Recount-leg fixture pair (small synthetic `.rkdb` dumps) driving the streaming diff GREEN/RED
- [x] Renderer fixture JSONs (two arms, one k) exercising entry-rate/byte-rate/asymmetry/predicted-vs-measured sections
- [x] Known-flake note: `scripts/bench/tests/test_verify_threads.py::TestNegativeControls::test_pre_engine_n_plus_one_stub_is_measured_red` — pre-existing ~50% macOS `sample`-race flake (STATE.md); purge stale `target/` before trusting a red

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Full-scale counterbalanced merge session at both k completes with parity green before timing and the verdict recorded via exit code | MBENCH-03 | Live multi-hour session on 86.74 GiB artifacts — the deliverable itself | ✅ Executed in-plan (12-02, 6h47m): parity green both k before timing, exit code 0 (NO-INVEST) recorded — evidence 12-VERDICT.json + 12-REVALIDATE.json + 12-PARITY-K{21,31}.json + 12-RESULTS-FULL-K{21,31}.json |
| Predicted-vs-measured reconciliation at full scale | MBENCH-04 | Compares live measurements against 11-LADDER-RESULTS.json predictions | ✅ Executed in-plan (12-02): all four rows +8.7–17.6%, reconciled against the ladder linearity caveat in 12-MERGE-REPORT.md + SUMMARY |

*All other phase behaviors have automated verification.*

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 60s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** validated 2026-11-17 (both phase requirements COVERED — 0 MISSING, 0 PARTIAL; manual-only rows executed in-plan with committed evidence)

## Validation Audit

- **Date:** 2026-11-17
- **Gaps found:** 0
- **Resolved:** 0
- **Escalated:** 0
- **Notes:** Post-execution audit (State A). 73-test Wave-0 suite green; Leg-2 recount implemented + tested (16 test refs); all five session evidence JSONs committed; manual-only rows executed during 12-02 with the verdict recorded (NO-INVEST, exit 0).

## Validation Audit 2026-11-17

| Metric | Count |
|---|---|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |
