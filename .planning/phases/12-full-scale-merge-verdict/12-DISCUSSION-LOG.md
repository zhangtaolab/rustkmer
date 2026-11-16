# Phase 12: Full-Scale Merge Verdict - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-11-17
**Phase:** 12-Full-Scale Merge Verdict
**Areas discussed:** Session controller, Session scheduling, Post-verdict wrap-up, Pre-session hygiene

---

## Area Selection

`--auto` mode: all 4 gray areas auto-selected.

---

## Session controller

### Q1: How is the multi-hour session driven?

| Option | Description | Selected |
|--------|-------------|----------|
| Staged controller (recommended) | `phase11.py` modeled on phase10.py — stage isolation, 0/1/2 contract, per-stage resume; mechanically pins stage order so the WR-01 constraint holds by construction | ✓ |
| Direct bench.py stages | Fewer moving parts, but stage order and resume live in operator memory | |
| No controller | Single monolithic run — a mid-session failure loses everything | |

**User's choice:** Staged controller (auto-selected recommended)
**Notes:** WR-01 (in-process deep leg OOMs at full scale) makes stage order structural, not advisory.

---

## Session scheduling

### Q1: One session or two?

| Option | Description | Selected |
|--------|-------------|----------|
| Single session both k (recommended) | One round-0 gate block, parity, then 3 counterbalanced reps per arm × both k; D-12 per-rep disk re-checks guard every rep | ✓ |
| Two sessions by k | Cleaner failure isolation but repeats round-0 gates and doubles session boundaries | |
| Extra reps (5) | Tighter CV but ladder showed linear scaling (ratios 1.06–1.37) — extra reps buy little | |

**User's choice:** Single session both k, exactly 3 reps (auto-selected recommended)
**Notes:** Protocol minimum ≥3; ladder linearity makes extra reps low-value.

### Q2: Wrap-up tasks home?

| Option | D-03 cleanup | D-04 report rewrite |
|--------|--------------|---------------------|
| Phase 12 wrap-up tasks (recommended) | Cleanup after verdict evidence committed (closes Phase 11 D-02 lifecycle) | Rewrite once with fresh verdict data (closes D-05) | ✓ |
| v2.1-close quick tasks | Later, detached from fresh verdict data | |
| Manual/later | Risks forgotten cleanup; report stays stale | |

**User's cleanup choice:** Phase 12 wrap-up (auto-selected recommended)
**User's rewrite choice:** Phase 12 wrap-up (auto-selected recommended)

---

## Pre-session hygiene

### Q1: When do the 3 pre-existing test reds get fixed?

| Option | Description | Phase 12 plan scope? | Selected |
|--------|-------------|---------------------|----------|
| Quick task before planning (recommended) | `/gsd-quick` retargets test_phase10_verdict.py paths; WR-04 README fix may fold in same touch; Phase 12's "zero new failures" discrimination restored | No — stays out of phase plans | ✓ |
| Carry as known-red | Suite stays red through the verdict session | | |
| Fix inside Phase 12 | Scope creep into a measurement phase | | |

**User's choice:** Quick task before planning (auto-selected recommended)
**Notes:** Verifier recommendation; CI command exits non-zero until fixed.

---

## Claude's Discretion

- Controller stage granularity and resume-point placement (phase10.py precedent governs)
- Parity execution mechanics per PARITY-GATE.md (streaming deep leg is the only full-scale route)
- Renderer extension details; entry-rate/byte-rate formulas per MBENCH-04
- Counterbalanced arm ordering via existing round_schedule machinery
- WR-02 opportunistic same-touch fix if renderer is extended
- Predicted-vs-measured check inputs from 11-LADDER-RESULTS.json

## Deferred Ideas

- MBF-01 flag sweep — post-verdict v2.2+, only on INVEST
- KMC3 — descoped 2026-11-16
- Mixed-canonicality/mixed-k arms — documented jellyfish bug, not an axis
- Phase 13 overlap — independent research, may run in parallel with this window

## (auto mode record)

- All questions auto-selected the recommended (first) option, single pass, no AskUserQuestion.
- Total: 4 areas, 5 questions, 0 user prompts.
