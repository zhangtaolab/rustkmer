---
phase: "12"
slug: "full-scale-merge-verdict"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
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
| (planner pins) | TBD | 0 | MBENCH-03 | TBD | controller stage isolation + exit-code contract (0/1/2; infra → 2) | unit | `.venv313/bin/python -m pytest scripts/bench/tests/test_phase11_verdict.py -q` | ❌ W0 | ⬜ pending |
| (planner pins) | TBD | 0 | MBENCH-03 | TBD | round-0 revalidate drift fails loud; anchor equality from manifest records | unit (fixtures) + in-stage verb | pytest test_phase11_verdict.py + `prepare_inputs.py revalidate` in-stage | verb ✅; gate ❌ W0 | ⬜ pending |
| (planner pins) | TBD | 0 | MBENCH-03 | TBD | counterbalanced schedule shape (3 arms × 3 reps, rotated starts) | unit | schedule-shape test over `rotation_schedule` | ❌ W0 (function ✅ output_stage.py) | ⬜ pending |
| (planner pins) | TBD | 0 | MBENCH-03 | TBD | parity legs green before results acceptance; Leg-2 recount diff raises on first mismatch | unit (fixture dumps) + live evidence | pytest test_phase11_verdict.py (streaming pipeline fixtures) | ❌ W0 (Leg-2 is new code) | ⬜ pending |
| (planner pins) | TBD | 0 | MBENCH-04 | TBD | renderer: no measurement literals; entry-rate/byte-rate formulas; asymmetry sentence; predicted-vs-measured caveat | unit | pytest test_phase11_verdict.py (renderer tests) | ❌ W0 | ⬜ pending |
| (planner pins) | TBD | 0 | MBENCH-04 | TBD | byte-identical re-render proof | unit (render twice, byte-compare) + in-stage proof | renderer test + recorded render-stage proof | ❌ W0 (pattern ✅ phase10/bench) | ⬜ pending |
| (session) | TBD | — | MBENCH-03 | — | full-scale session itself | session evidence | staged runs; gates green + schema-valid results + recorded exit code | n/a — the deliverable | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `scripts/bench/tests/test_phase11_verdict.py` — controller contract (stages, exit codes, schedule shape, Leg-2 recount fixtures, renderer byte-identity + metric formulas); covers the MBENCH-03/04 unit surface
- [ ] Recount-leg fixture pair (small synthetic `.rkdb` dumps) driving the streaming diff GREEN/RED
- [ ] Renderer fixture JSONs (two arms, one k) exercising entry-rate/byte-rate/asymmetry/predicted-vs-measured sections
- [ ] Known-flake note: `scripts/bench/tests/test_verify_threads.py::TestNegativeControls::test_pre_engine_n_plus_one_stub_is_measured_red` — pre-existing ~50% macOS `sample`-race flake (STATE.md); purge stale `target/` before trusting a red

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Full-scale counterbalanced merge session at both k completes with parity green before timing and the verdict recorded via exit code | MBENCH-03 | Live multi-hour session on 86.74 GiB artifacts — the deliverable itself | Run the staged session (`phase11.py`); verify revalidate/parity stage gates green, results schema-valid, exit code recorded and matches the verdict rule |
| Predicted-vs-measured reconciliation at full scale | MBENCH-04 | Compares live measurements against 11-LADDER-RESULTS.json predictions | Review rendered report's predicted-vs-measured section; deviations are findings to record, not silent failures |

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
