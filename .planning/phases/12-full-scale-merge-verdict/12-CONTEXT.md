# Phase 12: Full-Scale Merge Verdict - Context

**Gathered:** 2026-11-17
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 12 executes the pre-registered full-scale merge verdict session: at both k=21 and k=31, `rustkmer merge` and `jellyfish merge` run counterbalanced (≥3 reps per arm) at full scale over identical, parity-validated input artifacts (already built in Phase 11), with the three-way parity gate (including the per-k-mer deep leg) green BEFORE any timing; the invest/no-invest verdict is recorded via the 0/1/2 exit-code contract and rendered as a mechanical report with byte-identical re-render proof, entry-rate/byte-rate metrics, the disclosed single-threaded-comparator asymmetry, and a predicted-vs-measured cost-model check. This is the milestone v2.1 headline deliverable.

**No new measurement capabilities** — this phase RUNS what Phases 10-11 built. Defaults-only flags during the bench (a flag sweep is post-verdict v2.2+ work, only on INVEST). No KMC3 arm (descoped); no mixed-canonicality/mixed-k arms (jellyfish's silent canonicality acceptance is a documented bug, not a comparison axis). No Rust code changes.

</domain>

<decisions>
## Implementation Decisions

### Session Controller
- **D-01:** Phase 12 creates a **staged controller (`phase11.py`)** modeled on the `phase10.py` precedent — stage isolation, the 0/1/2 exit-code contract as the verdict carrier, and per-stage resume. The controller mechanically pins the stage order (revalidate → parity → timed rounds → verdict → render) so the WR-01 constraint (deep leg via the streaming form, never bench.py's in-process comparator at full scale) is enforced by construction, not by operator memory. — **Reversibility:** reversible — a code artifact; the session can be re-driven.

### Session Scheduling
- **D-02:** A **single staged session covers both k** — one round-0 gate block (artifact fingerprint + Total revalidation from 11-PREPARE-RECORD.md records, full disk-budget check against the 136 GiB derived floor), then parity execution, then exactly **3 counterbalanced reps per arm at each k** (the protocol minimum; the ladder showed linear scaling with tight ratios, so extra reps buy little). The D-12 per-rep light disk re-check runs before every measured rep. — **Reversibility:** reversible — the schedule is replannable until round 0 commits; after that the session's own resume contract carries it.

### Post-Verdict Wrap-Up (all inside Phase 12)
- **D-03:** **Artifact cleanup is a Phase 12 wrap-up task**, executed only after the verdict evidence (report + results JSON + exit-code record) is committed: delete the 8 artifacts under `/Users/forrest/Data/data/illumina/CRR1936095-merge-inputs/` (~86.74 GiB) per D-02 of Phase 11's lifecycle ("keep until the Phase 12 verdict lands, then clean up"). Rebuild remains possible via the 11-02 stage (~30-90 min), so nothing one-way is destroyed.
- **D-04:** The **full v2.0+verdict-based rewrite of `docs/benchmark-report.md` is a Phase 12 wrap-up task** (closes the D-05 deferred item from Phase 11) — the verdict data is fresh in-phase, so the doc is rewritten exactly once, including the merge-verdict sections, the superseded-banner removal, and current dataset/verdict numbers.

### Pre-Session Hygiene
- **D-05:** The **3 pre-existing test reds** (`scripts/bench/tests/test_phase10_verdict.py` archived-path failures, caused by commit 97c497c moving Phase-10 artifacts to `.planning/milestones/v2.0-phases/`) are fixed by a **`/gsd-quick` task BEFORE Phase 12 planning** — not inside Phase 12 plans. Rationale: the verifier recommended it; Phase 12's own "zero new failures" gate discrimination is meaningless while the suite carries known reds, and the harness CI command exits non-zero until the paths are retargeted. The same quick task may fold the WR-04 README rehearsal-command fix (missing `--input`/`--k` brace/`--disk-floor-gb 2`) as an adjacent doc correction.

### Carried Constraints from Phase 11 (locked, not re-decided)
- Parity-before-timing: the three-way gate (`rustkmer merge == independent recount of union == jellyfish merge`, exact per k-mer, `total_kmers` definition named per check) executes green before any timed round (MBENCH-03 success criterion 1).
- The full-scale deep leg runs the **streaming form** (PARITY-GATE.md §4 / `merge_characterize` streaming comparator) — bench.py's in-process dump-vs-dump is unit-level only (WR-01: it needs ~120-150 GB heap at the 10% rung).
- Input equivalence: both tools merge their own representation of identical, parity-validated source data (fingerprints + Totals revalidated from 11-PREPARE-RECORD.md before round 0 — Phase 11 D-04).
- Defaults-only flags during measurement; wall time is the primary decision axis; `max(rss, phys_footprint)` and disk recorded as context; BOTH verdict outcomes are valid results.
- Disk floor 136 GiB (derived, tripwire-pinned) guards the session; `--disk-floor-override` only for deliberate runs.
- Like-for-like `rustkmer merge --num-threads 1` arm is mandatory in the methodology block; t1 = 2-OS-thread pool contract (research A6).

### Claude's Discretion
- Controller stage granularity (how many stages, their names, resume-point placement) — phase10.py precedent governs.
- Parity execution mechanics at full scale (recount leg sizing, streaming deep-leg invocation, runtime) per PARITY-GATE.md.
- Report rendering details — extend the existing renderer patterns; entry-rate/byte-rate metric formulas per MBENCH-04.
- Counterbalanced arm ordering within the 6-arm merge round schedule (bench.py `round_schedule` machinery already generalizes).
- Predicted-vs-measured check inputs (ladder slopes from 11-LADDER-RESULTS.json; backstop caveat per milestone Pitfall 14).
- WR-02 (render-report default-out clobbering) may be fixed opportunistically in the same touch if the renderer is extended (HYG-04-style same-touch rule).

### Folded Todos
(None — todo_count was 0 at `todo.match-phase`.)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 11 outputs (the session's direct inputs)
- `.planning/phases/11-merge-characterization-harness-prep/PARITY-GATE.md` — the written three-way gate spec; §4 streaming deep-leg form is the ONLY full-scale deep-leg route (WR-01)
- `.planning/phases/11-merge-characterization-harness-prep/11-PREPARE-RECORD.md` — per-artifact sha256 + Total + command line; Phase 12 round-0 revalidation consumes these records verbatim (Phase 11 D-04)
- `.planning/phases/11-merge-characterization-harness-prep/11-LADDER-RESULTS.json` — fitted slopes + full-scale merge-wall predictions (rustkmer 53.8/73.4 s; jellyfish 77.3/105.5 s) feeding MBENCH-04's predicted-vs-measured check
- `.planning/phases/11-merge-characterization-harness-prep/11-FLOOR-DERIVATION.md` — the 136 GiB derived floor and its inputs
- `.planning/phases/11-merge-characterization-harness-prep/11-CONTEXT.md` — Phase 11 user decisions D-01..D-12 (artifact lifecycle, retention, floor policy)
- `.planning/phases/11-merge-characterization-harness-prep/11-REVIEW-DISPOSITION.md` — WR-01/02/03/04 + IN-01..05, all open (triage inputs for this phase's opportunistic fixes)

### Requirements & roadmap
- `.planning/REQUIREMENTS.md` — MBENCH-03/04 definitions and the MBENCH-02→Phase-12 mapping note
- `.planning/ROADMAP.md` §Phase 12 — success criteria 1-4 + Note (defaults-only, no KMC3, no mixed arms)
- `.planning/PROJECT.md` — v2.0 verdict numbers (144.69/147.08 s walls; 43.97/68.52 GiB MEM references) and guardrails

### Milestone research (protocol provenance)
- `.planning/research/SUMMARY.md` + `.planning/research/PITFALLS.md` — Pitfalls 1 (canonicality), 5, 7, 8, 14 (slice-number discipline) bind the session
- `.planning/research/STACK.md` — jellyfish 2.3.1 pinned semantics (single-threaded streaming merge, no `-t`/`-s` on merge)

### Harness code (execution surface)
- `scripts/bench/bench.py` — counterbalanced protocol, `round_schedule`, parity gates, disk floor guard, renderer, SCHEMA_VERSION 1
- `scripts/bench/phase10.py` — staged controller precedent (0/1/2 exit-code contract, stage isolation, resume)
- `scripts/bench/prepare_inputs.py` — `revalidate` verb (round-0 gate) + manifest schema
- `scripts/bench/merge_characterize.py` — streaming dump-vs-dump deep gate form (full-scale route)
- `scripts/bench/README.md` — stage docs; WARNING-2 fixed; WR-04 rehearsal-command defect noted

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `phase10.py` staged-controller pattern — template for `phase11.py`: per-stage exit codes, stage-isolated artifacts, resume from any completed stage
- `bench.py` protocol machinery — 7-arm counterbalanced rounds, medians + CV%, honest per-rep `cache_state`, fingerprints, schema v1, exit-3 disk guard: all driven as-is, no rewrite
- `prepare_inputs.py revalidate` — the round-0 gate is a single verb call over 8 manifest records
- `merge_characterize.py` streaming comparator — the proven full-scale deep-leg form (ran green at 318.5M/373.0M entries in Phase 11)
- Renderer (`_arm_row` merge `n/a` special case stays load-bearing) — extend for merge-verdict rows; byte-identical re-render proof pattern exists from Phase 10

### Established Patterns
- Parity-before-timing (locked v2.0 + Phase 11 precedent) — session order is fixed: revalidate → parity → timed rounds
- Provenance on every result: sha256 + commit + build profile + command line; honest `cache_state`
- Both verdict outcomes are first-class results (v2.0 precedent: verdict recorded either way, exit code carries the decision)
- Evidence JSON per stage, committed — rehearsal/ladder/prepare records are the pattern

### Integration Points
- Artifacts root: `/Users/forrest/Data/data/illumina/CRR1936095-merge-inputs/` (8 artifacts, 86.74 GiB, manifest `stage: complete`)
- Dataset root: `/Users/forrest/Data/data/illumina/CRR1936095_r1.fq.gz.split/` (recount leg reads part_001+part_006 source reads)
- Disk floor: `DEFAULT_DISK_FLOOR_GB = 136` tripwire-pinned to the derivation; floor formula consumes PREPARE-RECORD + LADDER-RESULTS
- Union anchors: k=21 → 8,967,099,203; k=31 → 8,275,694,030 (exact round-0 equality targets)
- Known flakes: the `test_verify_threads.py` ~50% macOS `sample`-race flake (STATE.md) — purge stale `target/` before trusting a red

</code_context>

<specifics>
## Specific Ideas

- The session is deliberately boring: every risky unknown was retired in Phase 11 (artifacts pre-built and anchor-exact, parity proven at slice scale twice, scaling linear, floor derived from measurements). Phase 12's planning is protocol scheduling, not investigation — ROADMAP marks the research flag "none".
- WR-01 is the one live hazard: a naive full-mode run would OOM after hours of reps with nothing saved. The controller's stage order is the structural fix (deep leg streamed, results persisted per stage before the next stage starts).
- Ladder predictions give MBENCH-04 its expected bands: measured merge walls should land near 54/73 s (rustkmer) and 77/106 s (jellyfish); large deviations are findings, not failures — record and reconcile against the linearity caveat.

</specifics>

<deferred>
## Deferred Ideas

- **MBF-01 flag/config sweep** — post-verdict v2.2+ work, only if the verdict is INVEST (ROADMAP Note).
- **KMC3 arm** — descoped 2026-11-16 (memory bar = below jellyfish; see memory notes).
- **Mixed-canonicality / mixed-k arms** — not a comparison axis (documented jellyfish bug).
- **Phase 13 overlap** — Producer Attribution Research is independent and may run in parallel with this phase's window (measurement-only, no code changes), per ROADMAP execution order.

</deferred>

---

*Phase: 12-Full-Scale Merge Verdict*
*Context gathered: 2026-11-17*
