# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

## Milestone: v1.0 — Performance

**Shipped:** 2026-10-20
**Phases:** 4 | **Plans:** 31 (of which 12 were Phase-3 gap-closure rounds) | **Sessions:** multi-session per phase (per-plan durations logged in archived STATE history)

### What Was Built
- CI merge gate (fmt / clippy `-D warnings` / test / pyo3 wheel build, 3-OS) + library hygiene: `log` facade, single-source `.rkdb` write, English-only strings (syn-enforced)
- Lock-free multi-core counting on both surfaces (DashMap + rayon, `--threads` chain, GIL release) with 1-vs-N golden-baseline differential proofs
- Bounded-memory merge (header-only admission control, streaming / prefix-cache routing, RAII temp lifecycle + TTL sweep, shared CLI/Python entry point) and dense u64 counting storage for k ≤ 32 (~0.52× bytes/entry, `.rkdb` v2 byte-identical)
- Reproducible benchmark harness + CI regression gate (25% wall / 15% RSS thresholds, per-platform committed baselines, full/slice/synthetic ladder) and the human-scale Jellyfish2 verdict: k=31 faster AND leaner; k=21 ~5x slower — honestly recorded and accepted as a known gap

### What Worked
- Golden-capture-first (D-10): committing pre-refactor baselines before every risky swap caught real drift (03-03's 2-character transcription error; PCOUNT-04's exact-count parity)
- Verification-driven gap closure: `03-VERIFICATION.md` gaps opened four closure rounds that fixed genuinely broken things (an endianness heuristic corrupting counts > 1M, a truncating streaming merge, an inverted density claim) — the verifier was worth the rounds
- Mutation-tested gates: proving a new test CAN fail (inject a defect, watch it go red, revert) turned several vacuous-green gates into real ones
- Honest measurement discipline: counterbalanced reps, per-rep cache_state recording, parity gates before timing, mechanically rendered reports — a measured NO (BENCH-02 k=21) was escalated and accepted rather than tuned away

### What Was Inefficient
- Phase 3 needed 17 plans (12 in gap-closure): several defects (endianness heuristic, strand-dropping iterator, silent partial merges) predated the phase and surfaced only once the streaming route became the default — earlier route-parity differentials would have caught them sooner
- Bookkeeping drift: REQUIREMENTS.md BENCH-02 was flipped `[x]` by a bookkeeping commit while the committed report said NO (W2) — the checkbox consumer trusted frontmatter over the evidence
- 46 commits sat unpushed for days; the windows-latest clippy leg never ran against 4 code commits until the close-day push (W1)
- Tooling format mismatches: 03-17-SUMMARY frontmatter unparseable YAML; legacy Phase 1/2 SUMMARYs lack `requirements-completed`, forcing manual cross-checks in the audit

### Patterns Established
- Observe, never re-derive: `stored_key_bytes()`/`uses_dense_storage()` read the LIVE variant; budget assertions derive from `estimate_total_kmers`, never hard-coded constants
- One door per fact: `read_header_of` is the only way merge routes learn input shape; `parse_memory_size` is shared by CLI and Python; the admission constant is computed once
- Route claims need route proofs: a "streaming route" test arm must prove the route itself (temp-dir probe), not just the output
- Per-item cfg gating over file-top allows (keeps `-D warnings` meaningful for platform-dead code)

### Key Lessons
1. Density lives on the table, not the key — an enum key pays max-variant size (32 B) whichever arm is populated; `CounterTable::Dense/Wide` is what actually halves memory
2. A GREEN gate that cannot fail reports nothing — mutation-test every verification gate once
3. Two sites computing the same quantity with two literals WILL drift — single-source constants and pair copies behaviorally (parse the echoed figures, don't compare comments)
4. Honest measurement beats a tuned verdict: BENCH-02's k=21 NO, escalated and accepted with v2 work staged, preserved more trust than a massaged YES would have
5. Push early: CI only gates what it can see; long unpushed tips accumulate unvalidated assumptions

### Cost Observations
- Model mix: not recorded this milestone (start tracking at v2)
- Sessions: Phases 1–2 completed 2026-07-01 in one day each; Phase 3 was the long tail (2026-10-07→10-09, 4 verification rounds); Phase 4 ran 2026-10-10→10-18 including a 3.2 h full-scale benchmark
- Notable: per-plan execution averaged ~17 min excluding benchmark wall-clock; verification rounds (not execution) dominated Phase 3 elapsed time

---

## Milestone: v2.0 — k=21 Counting Parity

**Shipped:** 2026-11-14
**Phases:** 6 (5-10) | **Plans:** 29 | **Tasks:** 73 | **Requirements:** 17/17 in-scope (BENCH-V2-01 descoped; MINIM deferred)

### What Was Built
- A standing measurement harness: slice parity gate with pinned reference, binary provenance on every artifact, `--threads` reality/scaling gates, contention attribution, Python baseline, and the CLI-vs-Python N-read differential (Phase 5)
- A working `--threads`, thread-local counters with end-of-run checked reduction, and a rolling 2-bit encoder with bit-parallel reverse complement (Phase 6)
- One shared counting engine — persistent workers, disjoint hash-range partition tables, overlapped producer/consumer — consumed by both the CLI and `PyCounter` (Phase 7)
- A parallel unstable sort + streaming write through the frozen `.rkdb` writer, with byte-identity proven through both binary-search consumers and a full differential matrix (Phase 8)
- Python parity: the shared engine behind `PyCounter`, D2 skip-N unified, sort-once `save_database`, frozen 12-name API, measured 2.35x/8.71x wins vs the committed baseline (Phase 9)
- The milestone verdict: **overall YES** at k=21 and k=31 on both surfaces, with exact count parity and lower peak memory than jellyfish (Phase 10)

### What Worked
- Profiling before architecture: the k=21 gap was parallel-scaling efficiency, not data structures — the research phase (D1) prevented a minimizer detour that would not have fixed the real bottleneck
- Parity-before-timing everywhere: every optimized path shipped with exact-count gates; the numbers in the final verdict are defended by committed, recomputable artifacts
- Mechanical rendering: the report is the renderer's output over committed documents, so every disclosure (KMC3 descope, cache census, dev-host, cross-session divergence) is enforced by code rather than by memory
- Adversarial code review caught real verdict-integrity holes (partial-k rendering, non-finite medians, medians-vs-reps disagreement, preflight budget tampering) and each fix landed with a regression test
- Two human checkpoints kept the expensive Python run authorized by measured CLI facts, not by estimates

### What Was Inefficient
- The k=31 jellyfish slowdown (23 min/rep in the CLI session vs 3 min in the Python session) was not predicted by the 5M-read probe; it doubled the CLI stage's planned duration and produced a disclosed 7.38x cross-session outlier
- Plan/harness interface drift: plan 10-04's render command and verdict schema were stale versus the tested harness, forcing an executor-side adaptation that had to be documented
- The first code-review pass found the deliverables had not been regenerated after the fixes — a second round was needed purely to publish the fixed renderer's output
- Parallel verification agents clobbered a shared `/tmp` input and raced a binary swap; one scaling run had to be discarded and re-run in an isolated scratch directory
- Bookkeeping lag: ROADMAP/STATE sat at "2/4 plans" and "wave 3" until the orchestrator's transition, and the manager counted four phases as complete only after their verifier digests were refreshed

### Patterns Established
- **Gate from measurement, never from estimate**: the Python memory preflight is re-derived from the measured CLI distinct count and pinned to the harness budget constant
- **Same-session reference**: each surface's verdict compares against the jellyfish median measured in its own counterbalanced session; cross-session divergence is disclosed mechanically
- **Fail-closed evidence validators**: pinned k set, finite values only, medians recomputed from raw reps, input shas recomputed from live documents
- **Self-describing evidence corrections**: when metadata was corrected post-hoc, the artifact carries a dated correction block and the measured values are provably untouched
- **Review-to-artifact closure**: a fix that changes the renderer must regenerate the deliverables, or the committed report is not the renderer's output

### Key Lessons
1. A measurement harness is part of the measurement — the verdict is only as trustworthy as its validators.
2. Cross-session timing references can differ by more than an order of magnitude; report both and make no cross-session claim.
3. Estimate-based budgets are acceptable only when the estimate is re-derived from a measurement before it authorizes an expensive run.
4. When a fix changes a renderer, regenerate and re-commit the artifacts in the same review round.

### Cost Observations
- Model mix: not tracked
- Sessions: multi-session autonomous run (discuss → plan → execute waves → review/fix → verify → audit → archive)
- Notable: the full-scale measurement stage (~3 h 20 min CLI + ~2 h Python) dominated wall time; review/fix and verification ran within normal context budgets

## Milestone: v2.1 — Merge Verdict & Producer Research

**Shipped:** 2026-11-18
**Phases:** 3 executed (11-13; Phase 14 NOT EXECUTED by D3 NO-GO) | **Plans:** 15 | **Tasks:** 36 | **Requirements:** 11/14 satisfied; PEXT-03/PEXT-04 unexecuted by recorded decision; MEM-01 holds by status quo

### What Was Built
- Seven-arm counterbalanced merge comparison in bench.py + a prepare-inputs stage building 86.74 GiB of provenanced artifacts + the written three-way parity gate (`PARITY-GATE.md`) proven at slice scale and full scale (Phase 11)
- Full-scale merge verdict: **NO-INVEST** — rustkmer merge beats jellyfish merge at both k (63.34 / 82.86 s vs 88.44 / 114.70 s), parity green before any timed rep, mechanically rendered report (Phase 12)
- Full-scale producer stage attribution on the shipped engine + a two-ceiling predicted-win model + the recorded D3 **NO-GO** memo that leaves Phase 14 unexecuted (Phase 13)
- v2.0 evidence debt closed: benchmark report rewritten from committed evidence, Nyquist records for Phases 5-8, SECURITY.md verification for Phases 9-10, six-part ~16.7 GB dataset correction

### What Worked
- Pre-registration: the D3 bar (10.0% both-k conjunction), the 0/1/2 exit-code contract, and parity-before-timing were fixed in writing before any measurement — the NO-GO is defended by the rule, not by post-hoc judgment
- Protocol reuse: the Phase-10 staged-controller pattern scaled directly to merge (`phase11.py`) and to attribution (`phase13.py`); seams default to pinned constants but are injectable, keeping unit tests hermetic without real data
- Mechanical determinism: memo/report rendering is byte-identical across independent re-renders, and the renderer refuses docs whose caveat does not match its own constant
- Measurement refuted a stated expectation: route-send (not parse/extract) dominates the producer wall — recorded unsmoothed, and it is why extraction could not clear the bar

### What Was Inefficient
- Phase 12's live session hit a round-0 source-fingerprint lookup bug (dotted part names) that needed a Rule-1 fix + regression test mid-session; the session then ran 6 h 47 min
- The pre-measurement expectation (parse+extract ~85% of producer wall) was directionally wrong; earlier cheap instrumentation could have flagged route-send dominance, though the bar itself still had to be pre-registered
- Predicted-vs-measured merge walls missed by +8.7..17.6% on all four rows (warmups within −6.4..+3.1%), suggesting a uniform timed-window host-state factor
- Audit closeout shape mismatch: table-shaped deferred items are un-acknowledgeable via the CLI writer (a known limitation); the close halted until the file was reshaped to heading/bullet form

### Patterns Established
- **Pre-register the decision rule, then measure**: the bar, the exit-code contract, and the parity protocol are written before the data; NO is a first-class outcome
- **Staged controllers with injectable seams**: production byte-identical, unit tests hermetic
- **Record contradictions, never smooth them**: route-send dominance and the +8.7..17.6% prediction miss are in the record
- **Lifecycle-bound evidence**: artifacts are built, validated, and deleted by explicit path after the evidence commits; provenance survives the deletion

### Key Lessons
1. A pre-registered bar makes a NO-GO cheap to defend and impossible to retrofit.
2. Measure the stage split before predicting the win — the dominant term was not the one assumed.
3. Deleting multi-GiB measurement inputs is safe only after the evidence citing them is committed.
4. Write deferred items in heading/bullet form: the audit scanner reads GFM table rows but the acknowledge writer cannot modify them.

### Cost Observations
- Model mix: not tracked
- Sessions: multi-session autonomous run; full-scale measurement sessions dominated (Phase 12 P02: 6 h 47 min; Phase 13 P02: 2 h 19 min)
- Notable: 15 plans / 36 tasks; per-plan averages ~29 min (Phase 11), ~1 h 51 min (Phase 12), ~52 min (Phase 13) — measurement wall-clock, not agent time, is the cost driver

## Cross-Milestone Trends

### Process Evolution

| Milestone | Sessions | Phases | Key Change |
|-----------|----------|--------|------------|
| v1.0 | multi | 4 | GSD adopted on brownfield v0.5.0; verification-driven gap-closure loop established |
| v2.0 | multi | 6 | Autonomy scaled up: wave worktrees, two human checkpoints, adversarial review-fix loop, mechanical evidence rendering |
| v2.1 | multi | 3 executed + 1 conditional NOT EXECUTED | Pre-registered decision gates (D3) scaled to merge and attribution; a conditional phase's NOT-EXECUTED decision recorded as a deliverable |

### Cumulative Quality

| Milestone | Tests | Coverage | Zero-Dep Additions |
|-----------|-------|----------|-------------------|
| v1.0 | full suite 439/0 green | not tracked | stdlib-only benchmark harness (no new runtime deps) |
| v2.0 | 571 harness + 508 Rust + 179 pytest green (1 known macOS sampling flake) | not tracked | Phase-10 controller + mechanical renderer (stdlib only; no new runtime deps) |
| v2.1 | 644 harness + 508 Rust + 179 pytest green (1 known macOS sampling flake) | not tracked | Phase-11/12/13 controllers + renderers, parity gate, attribution driver (stdlib only; no new runtime deps) |

### Top Lessons (Verified Across Milestones)

1. Measure before architecting: v1.0's k=21 gap was diagnosed as parallel-scaling efficiency, and v2.0's engine fixed exactly that — the minimizer path would not have.
2. Make gates adversarial: mutation-RED proofs (v1.0) and inject-defect regression tests (v2.0 review fixes) are what distinguish a real gate from a vacuous green.
3. Evidence must be regenerated after any change to its producer; a committed report that no longer matches its renderer is a defect.
4. Honest NOs and disclosed outliers survive scrutiny; tuned or re-rolled numbers do not.
5. Pre-registered decision rules turn a NO into a cheap, defensible outcome — and a conditional phase's NOT-EXECUTED record is a deliverable, not a hole.
