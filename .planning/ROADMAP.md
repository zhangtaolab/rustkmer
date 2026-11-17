# Roadmap: rustkmer

## Milestones

- ✅ **v1.0 Performance** — Phases 1-4 (shipped 2026-10-20)
- ✅ **v2.0 k=21 Counting Parity** — Phases 5-10 (shipped 2026-11-14; v2.0's conditional Phase 11 not triggered)
- 🚧 **v2.1 Merge Verdict & Producer Research** — Phases 11-14 (in progress)

## Phases

<details>
<summary>✅ v1.0 Performance (Phases 1-4) — SHIPPED 2026-10-20</summary>

- [x] Phase 1: Foundation & Quality (4/4 plans) — completed 2026-07-01
- [x] Phase 2: Parallel Counting (5/5 plans) — completed 2026-07-01
- [x] Phase 3: Memory Safety (17/17 plans) — completed 2026-10-09
- [x] Phase 4: Benchmark & Validation (5/5 plans) — completed 2026-10-18

Full detail: [milestones/v1.0-ROADMAP.md](milestones/v1.0-ROADMAP.md) · Summary: [MILESTONES.md](MILESTONES.md)

</details>

<details>
<summary>✅ v2.0 k=21 Counting Parity (Phases 5-10) — SHIPPED 2026-11-14</summary>

**Milestone Goal:** Match or beat Jellyfish2 on human-scale k=21 counting (and k=31 under fair, matched-hash comparison) on BOTH the CLI and Python surfaces, closing the BENCH-02 gap outright.

- [x] Phase 5: Measurement & Regression Harness (7/7 plans) — completed 2026-11-12
- [x] Phase 6: Parallelism Correctness & Hot Path (5/5 plans) — completed 2026-11-12
- [x] Phase 7: Shared Counting Engine (4/4 plans) — completed 2026-11-13
- [x] Phase 8: Output Pipeline & .rkdb v2 Parity (4/4 plans) — completed 2026-11-13
- [x] Phase 9: Python Parity (5/5 plans) — completed 2026-11-13
- [x] Phase 10: Benchmark Verdict (4/4 plans) — completed 2026-11-14
- [ ] Phase 11: Minimizer Partitioning & Memory Ceiling — **DEFERRED** (D3 not triggered 2026-11-14: Stage A hit parity on both k and both surfaces and peak memory was below jellyfish; MINIM-01..03 deferred — permanently descoped 2026-11-16)

**Outcome:** overall **YES** — k=21 CLI 144.69 s / Python 165.05 s vs jellyfish 194.85 / 197.95 s; k=31 CLI 147.08 s / Python 178.22 s vs jellyfish 1380.92 / 187.14 s; exact count parity; lower peak memory than jellyfish at both k; dev-host evidence only. BENCH-V2-01 (KMC3) descoped 2026-11-13.

Full detail: [milestones/v2.0-ROADMAP.md](milestones/v2.0-ROADMAP.md) · Requirements: [milestones/v2.0-REQUIREMENTS.md](milestones/v2.0-REQUIREMENTS.md) · Audit: [milestones/v2.0-MILESTONE-AUDIT.md](milestones/v2.0-MILESTONE-AUDIT.md)

</details>

### 🚧 v2.1 Merge Verdict & Producer Research (Phases 11-14)

**Milestone Goal:** Decide where the next performance investment goes — benchmark `rustkmer merge` against `jellyfish merge` at full scale for a measured invest/no-invest verdict (wall time is the primary decision axis; jellyfish is the sole comparator), research the producer-bound counting bottleneck (parallel extraction) with predicted-win sizing and a conditional implementation phase (v2.0 D3 pattern), close v2.0 carry-forward hygiene gaps, and hold the memory-below-jellyfish guardrail (k=21 43.97 GiB / k=31 68.52 GiB references).

- [x] **Phase 11: Merge Characterization & Harness Prep** - Jellyfish-merge arms + the three-way parity gate defined in writing and proven at slice scale + intermediate-scale jellyfish merge characterization + full-protocol dress rehearsal; hygiene pulled forward (stale `docs/benchmark-report.md`, Nyquist 5-8, SECURITY.md 9/10) so nothing new cites stale evidence (completed 2026-11-17)
- [x] **Phase 12: Full-Scale Merge Verdict** - Counterbalanced merge benchmark at BOTH k with parity executed before timing (including full-scale per-k-mer deep validation); invest/no-invest verdict recorded via the 0/1/2 exit-code contract; mechanical report with methodology block + predicted-vs-measured cost-model check (completed 2026-11-17)
- [x] **Phase 13: Producer Attribution Research** - Full-scale stage attribution (inflate / parse / extract / route-send) on the SHIPPED engine at both k with fingerprinted builds; predicted-win model naming both ceilings; recorded D3 go/no-go memo (independent — may overlap Phases 11-12) (completed 2026-11-17)
- [ ] **Phase 14: Parallel Extraction** - CONDITIONAL (D3 gate): parallel producer with all ten engine invariants + MEM guardrail re-measured at full scale — executes ONLY if Phase 13's memo says GO and Phase 12's verdict is recorded (**NOT EXECUTED** — Phase 13's recorded decision is NO-GO, 2026-11-17)

## Phase Details

**Phase numbering:** continues from v2.0 (Phases 1-10 shipped, archived under `milestones/`); v2.0's conditional Phase 11 was never created (D3 not triggered 2026-11-14), so **v2.1 starts at Phase 11**. Integer phases are planned milestone work; decimal phases (e.g. 12.1) are urgent insertions created via `/gsd-phase --insert`.

**Execution order:** 11 → 12; 13 is independent of both and may overlap their window (measurement-only — it lands no changes, keeping Phase 12's merge numbers attributable to a stable binary); 14 is last and gated. Only two hard dependencies: 13 → 14 (the D3 gate) and 12 → 14 (provenance stability — a changed binary invalidates full-scale merge numbers). HYG-01 must land in Phase 11, before the Phase 12 verdict exists.

**Guardrails (bind every phase's success criteria):**
- Parity before timing: the three-way per-k-mer merge gate (`rustkmer merge == independent recount of the union == jellyfish merge`) executes and passes BEFORE any timed round — the locked v2.0 precedent, extended to merge.
- MEM guardrail: any landed performance change keeps full-scale peak RSS below jellyfish at both k (43.97 GiB at k=21, 68.52 GiB at k=31) — re-measured, never asserted.
- Exact u32 counts with fail-loud checked arithmetic at every new aggregate site — never saturating or wrapping (WR-02).
- `.rkdb` v2 byte-identity, single `format.rs` writer, frozen public CLI/Python APIs — any break is a surfaced user decision only.
- MSRV 1.82 / Python ≥3.11; zero new runtime dependencies for the PEXT track absent a measured gate (flate2 `zlib-rs` feature switch only if inflate measures ≥ ~20% of producer wall).
- Benchmark honesty: provenance (sha256 + commit + build profile) on every artifact, honest per-rep `cache_state`, medians of counterbalanced reps, jellyfish as the sole comparator; no memory-win claims over the streaming merge comparator (jellyfish merge runs at ~6.8 MB RSS — RSS is context, not a decision axis, for merge).

### Phase 11: Merge Characterization & Harness Prep

**Goal**: The merge comparison is safe to run before any multi-hour full-scale session is spent: the harness runs jellyfish merge arms under the counterbalanced protocol, the three-way parity gate is defined in writing and proven at slice scale, jellyfish merge's full-scale behavior is characterized, and every v2.0 evidence debt that could contaminate new measurements (stale benchmark report, Nyquist 5-8 gaps, SECURITY.md 9/10) is closed.
**Depends on**: Nothing (first v2.1 phase; builds on the shipped v2.0 harness — `scripts/bench/bench.py`, `phase10.py` staged-controller precedent)
**Requirements**: MBENCH-01, MBENCH-02, MBENCH-05, HYG-01, HYG-02, HYG-03, HYG-04
**Success Criteria** (what must be TRUE):
  1. The harness runs the extended merge arm set — per-part same-`-m/-s/-C` jellyfish count artifacts feeding a `jellyfish merge` command arm, alongside `rustkmer merge` and the like-for-like `rustkmer merge --num-threads 1` arm — under the existing counterbalanced protocol, with input fingerprints, provenance recording, and honest per-rep `cache_state` for every rep (MBENCH-01).
  2. The three-way parity gate exists in writing before round 0 — `rustkmer merge == independent recount of the union == jellyfish merge`, exact per k-mer, with the `total_kmers` definition (record-count vs sum-of-counts) named per check — and a full-protocol slice-scale dress rehearsal passes it, including the dump-vs-dump deep gate, before any timed round (MBENCH-02).
  3. The CI degradation rung for the merge arm passes on the existing synthetic two-part merge arm inside the existing results schema — no second results schema is created (MBENCH-05).
  4. `docs/benchmark-report.md` no longer presents the superseded v1.0 k=21 "+420%" verdict as current (superseded banner or v2.0-based regeneration), and the dataset description (six single-member gzip parts, ~16.7 GB total) is corrected in PROJECT.md/docs — BEFORE the Phase 12 verdict lands (HYG-01).
  5. Evidence debts are closed: Nyquist validation records exist for Phases 5-8 (HYG-02), SECURITY.md threat-model verification exists for Phases 9-10 (HYG-03), and every backlog 999.1-999.3 item whose file is touched by milestone work is resolved in the same touch — opportunistic, remaining items stay tracked and are not gate-blocking (HYG-04).

**Plans**: 8/8 plans complete

Plans:
**Wave 1**
- [x] 11-01-PLAN.md — Harness merge-arm extension: seven-arm counterbalanced set + ordering assertion + schema/renderer compat (MBENCH-01, MBENCH-05)
- [x] 11-02-PLAN.md — prepare-inputs stage: build/revalidate/manifest with -s derivation, union-anchor reconciliation, and provenance records (D-01/D-03/D-04 mechanics)
- [x] 11-03-PLAN.md — Evidence hygiene (docs): benchmark-report banner + dataset correction + drift sweep + hygiene record (HYG-01, HYG-04)
- [x] 11-08-PLAN.md — Evidence hygiene (records): Nyquist 5-8 via /gsd-validate-phase + SECURITY.md 9-10 via /gsd-secure-phase (HYG-02, HYG-03)

**Wave 2** *(blocked on Wave 1 completion)*
- [x] 11-04-PLAN.md — Three-way parity gate: written PARITY-GATE.md spec + implementation + live slice-scale proof (MBENCH-02)
- [x] 11-05-PLAN.md — Full-scale artifact builds: 8 per-part .rkdb/.jf with -s decision gate and manifest revalidation (D-01/D-02/D-04)
- [x] 11-06-PLAN.md — Characterization ladder: 2-point × both-k × both-tools with slope/linearity evidence (D-07/D-08/D-09)

**Wave 3** *(blocked on Wave 2 completion)*
- [x] 11-07-PLAN.md — Disk floor (derive/block/override/per-rep) + full-protocol dress rehearsal + README stage docs/WARNING-2 (D-10/D-11/D-12, MBENCH-02 proof, HYG-04)

**Research flag**: none — research is unusually complete (jellyfish merge semantics pinned on the installed 2.3.1 binary AND official source; harness integration points file:line-anchored). The one open question — jellyfish merge runtime/memory at 20-90 GiB — is closed by this phase's own intermediate-scale characterization.
**Note**: Phase 11 delivers MBENCH-02's gate (written spec + implementation + slice-scale proof); its full-scale execution, including the user-selected per-k-mer deep validation, runs inside Phase 12's protocol (MBENCH-03). Also decide here: reuse vs regenerate the per-part input artifacts (either way sha256 + Total revalidation before round 0), and re-derive the disk pre-flight from v2.0 measured DB sizes — expect to raise `--disk-floor-gb` (its 150 GiB default was sized for count artifacts; merge transients estimate 150-400 GiB).

### Phase 12: Full-Scale Merge Verdict

**Goal**: The user has a measured merge verdict: at both k, `rustkmer merge` and `jellyfish merge` have run counterbalanced at full scale over identical, parity-validated inputs, and an invest/no-invest decision is recorded via the exit-code contract in a mechanically rendered report — the milestone's headline deliverable, completed before any PEXT implementation could change the binary.
**Depends on**: Phase 11 (extended harness, written parity gate, characterization, green dress rehearsal)
**Requirements**: MBENCH-03, MBENCH-04
**Success Criteria** (what must be TRUE):
  1. At BOTH k=21 and k=31, ≥3 counterbalanced full-scale reps per arm complete with three-way parity executed and green BEFORE any timing — `rustkmer merge == independent recount of the union == jellyfish merge`, exact per k-mer (the user-selected full-scale deep validation; the independent recount leg is cheap enough that skipping saves nothing) — with input artifacts fingerprint- and Total-revalidated before round 0 (MBENCH-03).
  2. The invest/no-invest verdict is recorded, computed from recorded medians at stated threads via the 0/1/2 exit-code contract — wall time is the primary decision axis, `max(rss, phys_footprint)` and disk are recorded as context, and BOTH verdict outcomes are valid results (MBENCH-03).
  3. The report's methodology block captures threads/flags/merge-route/sha256 per arm — including the like-for-like `rustkmer merge --num-threads 1` arm — and discloses the single-threaded-comparator asymmetry in one stated sentence: each tool merges its own representation of identical, parity-validated input data (MBENCH-03).
  4. The merge-verdict report is mechanically rendered with a byte-identical re-render proof (no measurement literals in code), entry-rate / byte-rate metrics that make the inherent format asymmetry visible (`.jf` ~10 B/entry vs `.rkdb` 20 B/entry), and a predicted-vs-measured cost-model check (linear-in-entries, single-threaded) (MBENCH-04).

**Plans**: 4/4 plans complete

Plans:
**Wave 1**
- [x] 12-01-PLAN.md — Staged controller `phase11.py` (D-01) tracer slice: five-stage skeleton + 0/1/2 contract, verdict + render stages with byte-identity proof, defaults-only arm argv, contract test suite (MBENCH-03, MBENCH-04)

**Wave 2** *(blocked on Wave 1 completion)*
- [x] 12-04-PLAN.md — Controller expansion: round-0 revalidate stage (anchors + session budget), parity stage with the new Leg-2 recount diff (streaming, WR-01 fix), timed stage (3-arm counterbalanced), all unit-green on fixtures (MBENCH-03)

**Wave 3** *(blocked on Wave 2 completion)*
- [x] 12-02-PLAN.md — Full-scale session: round-0 revalidation → parity (both k, streaming deep legs) → timed (3 arms × 3 reps) → verdict (exit-code contract) → render (byte-identical proof), evidence committed per stage (MBENCH-03, MBENCH-04)

**Wave 4** *(blocked on Wave 3 completion)*
- [x] 12-03-PLAN.md — Wrap-up: `docs/benchmark-report.md` v2.0+verdict rewrite once from committed evidence (D-04) + merge-input artifact cleanup after evidence commits (D-03) (MBENCH-03, MBENCH-04)

**Research flag**: none — execution of a pre-registered protocol via a phase10-style staged controller (optional `phase11.py`); no unknowns beyond Phase 11's characterization output.
**Note**: Defaults-only flags during the bench — measure DEFAULTS first; a flag/config sweep is post-verdict work only on INVEST (MBF-01, deferred to v2.2+). No KMC3 arm (descoped 2026-11-16); no mixed-canonicality/mixed-k arms (both tools reject mixed-k; jellyfish's silent canonicality acceptance is a documented bug, not a comparison axis).

### Phase 13: Producer Attribution Research

**Goal**: The user knows where the producer wall actually goes on the SHIPPED engine at full scale — inflate vs parse vs extract vs route-send — and whether parallel extraction's predicted win clears the D3 bar, recorded as a go/no-go memo that either triggers Phase 14 or closes PEXT with evidence.
**Depends on**: Nothing (independent of Phases 11-12; may overlap their window — measurement-only, no code changes land, so Phase 12's merge measurements stay attributable to a stable binary)
**Requirements**: PEXT-01, PEXT-02
**Success Criteria** (what must be TRUE):
  1. A stage-attribution table exists for the shipped engine at BOTH k from fingerprinted builds: inflate / parse / extract / route-send shares measured at FULL scale via the plain-vs-gzip differential plus a pure-read control — no slice-scale number and no pre-Phase-7 profile feeds the gate decision (PEXT-01).
  2. The predicted-win model names BOTH ceilings — the parallelizable share and worker-side scaling — with every input number cited to a named full-scale source run (v2.0 measured walls: CLI 144.69 s k=21 / 147.08 s k=31; Python 165.05 s / 178.22 s) (PEXT-02).
  3. The D3-gate go/no-go decision is recorded as the research deliverable: either Phase 14 executes with cited evidence, or it does not fire and PEXT-03/PEXT-04 remain unexecuted by recorded decision (PEXT-02).

**Plans**: 3/3 plans complete

Plans:
**Wave 1**
- [x] 13-01-PLAN.md — Measurement driver tracer: phase13.py skeleton + probe materialization + rehearsal-mode end-to-end + full-scale stage functions + Wave-0 unit module; D3 bar pre-registered (PEXT-01, PEXT-02)

**Wave 2** *(blocked on Wave 1)*
- [x] 13-02-PLAN.md — Live session: D-03 fingerprint gate (re-measure) + D-04 decompression + full-scale counterbalanced A/B/C/D + control matrix at both k + attribution/predicted-win/decision blocks (PEXT-01, PEXT-02)

**Wave 3** *(blocked on Wave 2)*
- [x] 13-03-PLAN.md — Gate memo render + ROADMAP Phase 14 annotation (D-02) + D-04 input lifecycle (deletion after memo commit) (PEXT-02)

**Research flag**: none — the phase IS research, and its measurement design (arms A-D: stock / pre-decompressed / stage sub-timers / null consumer; controls; sizing model) is already specified in the milestone research; planning is protocol scheduling, not investigation.
**Note**: Expected outcome per current evidence — inflate ~13% of producer wall (below the ~20% zlib-rs gate), parse+extraction ~85%+, so zero-dependency extraction parallelization is the likely lever; no new instrumentation required for the headline numbers (`--features profiling` diagnostics exist). The dataset's six independent gzip parts give a producer-per-file topology six files to spread across if Phase 14 runs.

### Phase 14: Parallel Extraction

**Goal**: (Only if the Phase 13 D3 gate fires) the producer stage runs in parallel — records remain the unit of parallel work, the attach topology is decided in this phase's planning from Phase 13 attribution data — with all ten engine invariants preserved and the memory guardrail re-measured at full scale. If the gate does not fire, this phase does not execute and PEXT-03/PEXT-04 stay unexecuted by recorded decision.
**Depends on**: Phase 13 (D3 gate verdict — research gates implementation) AND Phase 12 (provenance stability — a changed binary invalidates full-scale merge measurements, so the verdict must be recorded first); reuses Phase 11's extended harness for scaling and parity gates
**Conditional**: D3 pattern (v2.0 precedent, reused) — executes ONLY if Phase 13's predicted-win memo says GO. On NO-GO the phase is marked NOT EXECUTED and PEXT-03/PEXT-04 remain unexecuted with the evidence trail. The recorded Phase-13 decision is NO-GO, recorded 2026-11-17 in `.planning/phases/13-producer-attribution-research/13-GATE-MEMO.md`.
**Requirements**: PEXT-03 (CONDITIONAL), PEXT-04 (CONDITIONAL), MEM-01
**Success Criteria** (what must be TRUE):
  1. Counts are exactly preserved under parallel extraction: `.rkdb` output byte-identical (sha256) across thread counts, 1-vs-N and old-vs-new differentials identical across the k × canonical × threads matrix, partition disjointness and conservation property tests green, and every new aggregate site fails loud with checked arithmetic (PEXT-03).
  2. The decided topology runs with all ten engine invariants green as named gates — honest thread-observability (extended if the topology changes the 2N+1 shape), flush/token happens-before, true `--threads 1` sequential path, bounded in-flight memory, frozen 12-name `PyCounter` surface, no-unwrap/error contracts, and clean teardown proven by error-injection tests at every boundary (PEXT-03).
  3. The MEM guardrail is re-measured, not asserted: full-scale peak RSS stays below the jellyfish references at both k (k=21 < 43.97 GiB, k=31 < 68.52 GiB) on the fingerprinted post-change build (PEXT-04, MEM-01).
  4. The gated win is realized: full-scale count wall at the decision-relevant thread count improves by a margin consistent with the Phase 13 predicted-win model, measured with parity-before-timing and provenance on every artifact.

**Plans**: TBD (only if the D3 gate fires)

**Research flag**: `--research-phase` required if triggered — attach topology decision (dispatcher-only rayon tasks that return buffers vs OS-thread extractors sending via cloned `SyncSender`s), flush-token contract for multi-sender producers (recommended: producers only route, caller flushes after a producer-join epoch), queue-depth sizing as a measured knob, warning-batch grouping contract decision, error-injection test matrix.
**Note**: Zero new runtime dependencies expected (`std::thread` + `sync_channel` + existing `PartitionLayout`/`RoutingBuffers`/`for_each_window` machinery); rayon is forbidden in blocking worker/extractor loops by the engine's documented contract. The flate2 `zlib-rs` feature switch joins only if Phase 13 measured inflate ≥ ~20% of producer wall.

## Progress

**Execution Order:**
11 → 12; 13 anytime after roadmap approval (independent, may overlap 11-12); 14 only if 13's D3 gate fires AND 12's verdict is recorded.

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Foundation & Quality | v1.0 | 4/4 | Complete | 2026-07-01 |
| 2. Parallel Counting | v1.0 | 5/5 | Complete | 2026-07-01 |
| 3. Memory Safety | v1.0 | 17/17 | Complete | 2026-10-09 |
| 4. Benchmark & Validation | v1.0 | 5/5 | Complete | 2026-10-18 |
| 5. Measurement & Regression Harness | v2.0 | 7/7 | Complete | 2026-11-12 |
| 6. Parallelism Correctness & Hot Path | v2.0 | 5/5 | Complete | 2026-11-12 |
| 7. Shared Counting Engine | v2.0 | 4/4 | Complete | 2026-11-13 |
| 8. Output Pipeline & .rkdb v2 Parity | v2.0 | 4/4 | Complete | 2026-11-13 |
| 9. Python Parity | v2.0 | 5/5 | Complete | 2026-11-13 |
| 10. Benchmark Verdict | v2.0 | 4/4 | Complete | 2026-11-14 |
| 11. Merge Characterization & Harness Prep | v2.1 | 8/8 | Complete    | 2026-11-17 |
| 12. Full-Scale Merge Verdict | v2.1 | 4/4 | Complete    | 2026-11-17 |
| 13. Producer Attribution Research | v2.1 | 3/3 | Complete    | 2026-11-17 |
| 14. Parallel Extraction | v2.1 | NOT EXECUTED | Not executed — D3 NO-GO (2026-11-17) | - |

## Backlog

### Phase 999.1: Follow-up — Phase 03 deferred UAT follow-up: Test 22 (BACKLOG)

**Goal:** Resolve the UAT checkpoint deferred during Phase 03 verification
**Source phase:** 03
**Deferred at:** 2026-10-09 during /gsd-verify-work 03 session completion
**Follow-ups:**
- [ ] Test 22: pyo3 0.27 no longer auto-emits -undefined dynamic_lookup; pyo3/build.rs should call pyo3_build_config::add_extension_module_link_args() so the documented manual-build workaround links as-is again (this session injected it via RUSTFLAGS) (deferred 2026-10-09). Caveat: if this lands, pyo3-build-config must be re-added as a `[build-dependencies]` entry in `pyo3/Cargo.toml` (removed by quick 261111-sq1 because build.rs does not call it today).

### Phase 999.2: Follow-up — Phase 03 deferred UAT follow-up: Test 22 (BACKLOG)

**Goal:** Resolve the UAT checkpoint deferred during Phase 03 verification
**Source phase:** 03
**Deferred at:** 2026-10-09 during /gsd-verify-work 03 session completion
**Follow-ups:**
- [ ] Test 22: dev-venv pitfall: a stale pyrustkmer 0.4.1 package directory in site-packages silently shadows a manually installed pyrustkmer.so extension (deferred 2026-10-09)

### Phase 999.3: Follow-up — Phase 03 deferred UAT follow-up: Test 21 (BACKLOG)

**Goal:** Resolve the UAT checkpoint deferred during Phase 03 verification
**Source phase:** 03
**Deferred at:** 2026-10-09 during /gsd-verify-work 03 session completion
**Follow-ups:**
- [ ] Test 21: deferred-items.md's claim that loose *.chunk files are never swept is stale — temp_lifecycle.rs now sweeps them (CHUNK_FILE_PREFIXES); update the record (deferred 2026-10-09)

*999.1-999.3 are handled opportunistically in v2.1 under HYG-04 (Phase 11): resolved in the same touch whenever milestone work touches their files — not gate-blocking.*

### v2.0 carry-forward (from the milestone audit, 2026-11-14 — status updated 2026-11-16)

- Phase 5/6/7/8 Nyquist coverage → **PROMOTED** to v2.1 requirement HYG-02 (Phase 11)
- `SECURITY.md` absent for Phases 9 and 10 → **PROMOTED** to v2.1 requirement HYG-03 (Phase 11); the 8 Info findings in `09-REVIEW.md` remain info-only and tracked
- `cargo fmt --all --check` drift → **RESOLVED** by quick 261116-ks7 (commit ee742dc)
- Benchmark harness WARNING-1 (CLI stage does not structurally consume the slice gate) and WARNING-2 (README pool-size formula drift) → opportunistic when `scripts/bench/` is touched (Phase 11 does touch it)
- MINIM-01..03 (minimizer partitioning / memory ceiling) → **PERMANENTLY DESCOPED** (user decision 2026-11-16: the memory bar is "below jellyfish", already met at both k; KMC-class RAM is not a goal)

### Deferred to v2.2+ (post-verdict; from REQUIREMENTS.md)

- **MBF-01**: rustkmer merge flag tuning / config sweep — only if the Phase 12 verdict says INVEST
- **MBF-02**: N-way merge scaling and r1+r2 input variants — post-verdict
- **PEXT-05**: extractor topology refinements beyond the first landed design — post-verdict
