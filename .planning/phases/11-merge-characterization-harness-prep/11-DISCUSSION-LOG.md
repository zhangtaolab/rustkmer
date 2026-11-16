# Phase 11: Merge Characterization & Harness Prep - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-11-16
**Phase:** 11-Merge Characterization & Harness Prep
**Areas discussed:** Input artifact rebuild & retention, Stale report resolution, Intermediate-scale characterization ladder, Disk pre-flight policy

---

## Area Selection

User selected all four proposed gray areas (multiSelect): Input artifact rebuild & retention, Stale report resolution, Intermediate-scale characterization ladder, Disk pre-flight policy.

---

## Input artifact rebuild & retention

### Q1: When are the full-scale merge input artifacts built?

| Option | Description | Selected |
|--------|-------------|----------|
| Pre-build in Phase 11 (recommended) | Dress rehearsal and characterization validate the real fingerprint/Total revalidation path; Phase 12 starts clean; +30–90 min setup in this phase | ✓ |
| Build at Phase 12 round 0 | Phase 11 lighter, but Phase 12 carries setup risk and longer round-0 wait | |
| Split by tool across phases | rustkmer side in Phase 11; jellyfish side after the count-B arm is proven | |

**User's choice:** Pre-build in Phase 11
**Notes:** Local disk verified first — no v2.0-era `.rkdb`/`.jf` artifacts survive anywhere, so regeneration is forced regardless.

### Q2: Retention policy?

| Option | Description | Selected |
|--------|-------------|----------|
| Keep until verdict lands (recommended) | All 8 artifacts stay on disk through the Phase 12 verdict, then cleanup; simplest, fingerprints computed once; ~70 GiB held | ✓ |
| Delete .jf after parity green | Saves ~22 GiB but `.jf` regeneration forces re-running jellyfish merge arms | |
| Delete after use, keep only fingerprints | Cheapest on disk but breaks the round-0 fingerprint-revalidation guardrail | |

**User's choice:** Keep until verdict lands
**Notes:** Disk arithmetic (345 GiB free vs 70 GiB artifacts + 150–400 GiB transients) made this a real tradeoff; user accepted the peak pressure.

### Q3: Where do the artifacts live?

| Option | Description | Selected |
|--------|-------------|----------|
| Dedicated dir next to data (recommended) | e.g. `/Users/forrest/Data/data/illumina/CRR1936095-merge-inputs/`; outside repo, no mis-commit risk | ✓ |
| In-repo scripts/bench/scratch/ | Convenient but large files in repo tree | |
| Planner decides | | |

**User's choice:** Dedicated dir next to data

### Q4: How are artifacts built / provenance recorded?

| Option | Description | Selected |
|--------|-------------|----------|
| Harness built-in stage (recommended) | prepare-inputs subcommand builds all artifacts + records sha256/Total/command-line provenance automatically; reproducible | ✓ |
| Manual runs + hand-recorded fingerprints | No new code but 8 hand-copied digests are error-prone | |
| One-off script outside bench.py | Middle ground, weaker reproducibility | |

**User's choice:** Harness built-in stage

---

## Stale report resolution

### Q1: How is docs/benchmark-report.md resolved (HYG-01)?

| Option | Description | Selected |
|--------|-------------|----------|
| Banner + deferred rewrite (recommended) | Superseded banner (pointing to v2.0 milestone evidence) + dataset correction now; full v2.0-based rewrite deferred until after the Phase 12 merge verdict so the doc is rewritten once | ✓ |
| Full v2.0 rewrite now | Doc immediately useful, but rewritten again after Phase 12 | |
| Banner + v2.0 summary section | Slightly more useful than a bare banner, much cheaper than a rewrite | |

**User's choice:** Banner + deferred rewrite
**Notes:** Rewrite recorded as a deferred idea (needs a home at v2.1 close).

### Q2: How wide is the drift-correction sweep?

| Option | Description | Selected |
|--------|-------------|----------|
| Named artifacts + grep sweep (recommended) | Fix the two named spots; grep docs/, README, USER_GUIDE, PROJECT_SUMMARY for same-class drift; factual fixes only | ✓ |
| Named artifacts only | Smallest scope; same-class drift elsewhere survives | |
| Full docs audit | Balloons into a docs-update exercise — out of Phase 11 scope | |

**User's choice:** Named artifacts + grep sweep

---

## Intermediate-scale characterization ladder

### Q1: How many scale points?

| Option | Description | Selected |
|--------|-------------|----------|
| Two-point ladder (recommended) | ~10% + ~40% part scale; slope + coarse linearity check; MBENCH-04 full-scale check is the backstop | ✓ |
| Three-point ladder | More confident fit, most runtime | |
| Single-point estimate | Cheapest; blind to non-linearity — the exact failure this characterization exists to prevent | |

**User's choice:** Two-point ladder

### Q2: What inputs?

| Option | Description | Selected |
|--------|-------------|----------|
| Real-data slice pairs (recommended) | Via existing random_slice/make_slice; full prepare→count→merge chain; also exercises prepare-inputs on real data | ✓ |
| Different real part pairs | Same size each → no scaling information | |
| Synthetic inputs | Fast/controllable but weaker extrapolation to real full scale | |

**User's choice:** Real-data slice pairs

### Q3: Which tools?

| Option | Description | Selected |
|--------|-------------|----------|
| Both tools (recommended) | rustkmer merge + jellyfish merge on the same pairs; MBENCH-04 gets a fitted curve; rustkmer scaling behavior visible early | ✓ |
| jellyfish only | Literal minimum from ROADMAP; cost-model check left with an assumed slope | |

**User's choice:** Both tools

---

## Disk pre-flight policy

### Q1: How is the raised floor determined?

| Option | Description | Selected |
|--------|-------------|----------|
| Derived formula from measured sizes (recommended) | Inputs + largest transient (ladder-extrapolated) + margin; written into bench default; auditable | ✓ |
| Fixed generous value | Simple but unjustified and blunt | |
| Lock constraints only | CONTEXT locks "derived from measured, must exceed 150" and planner derives | |

**User's choice:** Derived formula from measured sizes

### Q2: Behavior below the floor?

| Option | Description | Selected |
|--------|-------------|----------|
| Block + explicit override (recommended) | Hard fail with shortfall stated; `--disk-floor-override` for deliberate runs | ✓ |
| Hard block, no exception | Strictest; dead-ends when disk is temporarily tight | |
| Warn and continue | Risks mid-session disk exhaustion during multi-hour reps | |

**User's choice:** Block + explicit override

### Q3: When does the check run?

| Option | Description | Selected |
|--------|-------------|----------|
| Round-0 full check + per-rep light check (recommended) | Full budget before round 0; lightweight re-check each rep catches drift from other processes | ✓ |
| Round-0 only | Simplest; blind mid-session | |
| Every stage full check | Most conservative, diminishing returns | |

**User's choice:** Round-0 full check + per-rep light check

---

## Claude's Discretion

- Dress rehearsal breadth (full protocol, all arms, both k at slice scale)
- Parity-gate written spec location/format (content fixed by MBENCH-02)
- Characterization results format/location (existing evidence-JSON patterns)
- prepare-inputs stage CLI shape and naming
- Whether `phase11.py` staged controller is created now or deferred to Phase 12
- HYG-02/HYG-03 execution via the named workflows; HYG-04 stays opportunistic

## Deferred Ideas

- Full v2.0-based rewrite of `docs/benchmark-report.md` including merge-verdict sections — after the Phase 12 verdict lands (v2.1 close window)
