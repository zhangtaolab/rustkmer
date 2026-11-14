# Phase 10: Benchmark Verdict - Context

**Gathered:** 2026-11-13
**Status:** Ready for planning

<domain>
## Phase Boundary

Answer the milestone's acceptance question with honest, reproducible full-human-scale measurement on both surfaces. The deliverable is a verdict computed from recorded medians plus the evidence artifacts that support it — not new capability, not tuning, not a re-run-until-green exercise.

**Scope change ratified during this discussion:** the KMC3 comparison (BENCH-V2-01) is **removed from scope**. The user stated on 2026-11-13: "不需要KMC3，本项目与KMC3 无关". This supersedes the earlier D3 ruling that kept BENCH-V2-01 in v2.0. No third-party binary is downloaded or executed in this phase.

Out of scope: KMC3 (any form), CI-class baseline regeneration, minimizer/disk-backed implementation (Phase 11, still a D3 decision after the verdict), any performance change to the counting or output paths.

</domain>

<decisions>
## Implementation Decisions

### Run Scope and Staging
- Both surfaces are measured at full human scale: the CLI binary and the Python `pyrustkmer` counter.
- Input is the complete CRR1936095 read-1 set — both split parts (`part_001` + `part_006`, ~5.2 GB gzipped). A single part does not satisfy the human-scale requirement.
- Threads are matched across tools at 16 (all cores on the dev host): jellyfish `-t 16`, rustkmer `--threads 16`. A `t1` arm is recorded alongside as scaling evidence.
- Execution is strictly staged: slice gate (the 4M `part_001` slice with pinned parity) must be green first, then CLI full-scale, then Python full-scale. A failing stage stops the sequence — the later stages are not run on a broken foundation.

### KMC3
- **Dropped entirely.** No download, no install, no execution, no comparison. BENCH-V2-01 is descoped from v2.0 by user decision, and the verdict artifact must say so explicitly rather than silently omitting the section.
- The harness must not fail or warn-spam because KMC3 is absent; absence is the intended state for this phase.

### Measurement Protocol
- 3 reps per arm, counterbalanced (round-robin rotation) across arms, verdict computed from recorded medians — the v1.0 protocol.
- Cache state is recorded honestly per rep. Without sudo there is no cache purge, so reps record `unavailable` rather than claiming a cold cache; the report states this limitation plainly.
- Memory is reported as `max(rss, phys_footprint)` per the project's established convention.
- Dev-host evidence only. CI-class baselines are **not** regenerated from this host; a dev-host number must never be written into a CI baseline slot.

### Verdict and Phase 11 Trigger
- Both k values are measured: k=21 as the primary acceptance question, k=31 under fair matched-hash comparison to re-verify the v1.0 YES.
- The verdict is a strict comparison of recorded medians: `rustkmer_median <= jellyfish_median` is match-or-beat. No tolerance, no noise band, no re-roll.
- A NO is recorded honestly and stands. The phase never tunes parameters or re-runs until the result turns green.
- After the full-scale numbers land, the D3 decision (whether to build minimizer partitioning / a memory ceiling) is returned to the user as an explicit decision. Phase 11 is not auto-triggered by a threshold.

### Claude's Discretion
- Exact harness entry point and evidence file layout (extend `scripts/bench/` vs a new driver).
- Rep/arm scheduling details beyond counterbalancing.
- How the verdict report is rendered (markdown from recorded medians).
- Whether the Python full-scale arm reuses the Phase 9 `--compare-baseline` machinery or a phase-10-specific path.

### Post-Research Decisions (2026-11-13, after the research report)
- **Python OOM is a hard gate with a user stop.** Run the CLI full-scale arm first to obtain the measured distinct count; recompute the Python arm's memory budget from that measured value; if it projects over budget, STOP and ask the user. Never skip the Python arm silently, never auto-modify the engine to make it fit, and never report a blocked arm as a result.
- **The `t1` arm is CLI-only.** Roughly +9 minutes per rep, excluded from the acceptance rule, recorded as scaling evidence. No Python `t1` arm.
- **Two checkpoints.** First checkpoint: harness built + memory preflight + slice gate green + CLI full-scale measured. Second checkpoint: Python full-scale + the verdict. Do not run the Python arm or compute the verdict before the first checkpoint has been reported.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `scripts/bench/thread_scaling.py` — slice/full measurement with pinned parity, counterbalanced reps, provenance, cache_state.
- `scripts/bench/output_stage.py` — the arm/schedule/verdict pattern (round-robin rotation, medians, verdict computed from recorded values).
- `scripts/bench/bench.py` — `measure`, `binary_provenance`, `validate_schema`, `validate_provenance`, `reduce_arm`, `fingerprint`.
- `scripts/bench/python_bench.py` — the Python-surface harness from Phase 9, including `--compare-baseline` identity guards and the fresh-worker rusage protocol.
- `scripts/bench/baselines/slice_parity.crr1936095.json` — the committed slice parity reference (Distinct 229,694,874 / Total 519,271,168 at 4M reads).
- `scripts/bench/baselines/python_bench_baseline.darwin.json` — the committed Phase 5 Python sequential baseline.

### Established Patterns
- Parity before timing: exact counts and the input fingerprint are proven before any wall-clock is recorded.
- Provenance on every artifact: binary/module sha256, git commit, dirty flag, build profile.
- Exit contract: 0 = valid result, 1 = a genuine FAIL verdict (artifact kept), 2 = invalid measurement (no artifact).
- Never edit a committed baseline; a verdict artifact asserts the baseline's sha256 so tampering is detectable.

### Integration Points
- `jellyfish` 2.3.1 at `/opt/homebrew/bin/jellyfish`.
- Dataset at `/Users/forrest/Data/data/illumina/CRR1936095_r1.fq.gz.split/` (`part_001` and `part_006`, 2.6 GB each).
- `target/release/rustkmer`, rebuilt from the Phase 9 tree.
- `.venv313` for the Python surface.

</code_context>

<specifics>
## Specific Ideas

- The v1.0 verdict precedent is the template: medians of counterbalanced reps, honest per-rep cache_state, a mechanically rendered report, and a verdict computed from the recorded numbers rather than asserted.
- The Phase 9 `--compare-baseline` work makes a false PASS hard by construction (identity-guarded arms, worker-thread cross-checks). Any full-scale Python arm should reuse that discipline rather than re-deriving it.
- The KMC3 descope must be visible in the artifact and in REQUIREMENTS.md, not merely absent. A reader in six months must be able to see that it was a decision, not an oversight.
- The Phase 9 review left one directly relevant Info finding: the `--previous` differential loader accepts any structurally valid differential. If the phase-10 Python arm consumes any committed evidence, pin its sha256.

</specifics>

<deferred>
## Deferred Ideas

- KMC3 comparison — descoped by user decision, not deferred to a later phase.
- Minimizer partitioning / memory ceiling (Phase 11) — awaits the D3 decision after this phase's numbers.
- CI-class baseline regeneration — no CI-class baseline exists; Phase 10 records dev-host evidence only.

</deferred>
