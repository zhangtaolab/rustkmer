---
gsd_state_version: "1.0"
milestone: v2.1
milestone_name: Merge Verdict & Producer Research
current_phase: 14
current_phase_name: Parallel Extraction
current_plan: Not started
status: All phases complete (Phase 14 NOT EXECUTED — D3 NO-GO)
stopped_at: Phase 13 complete — Phase 14 not executed (D3 NO-GO); v2.1 ready to close
last_updated: "2026-11-17T15:30:17.669Z"
last_activity: 2026-11-17
last_activity_desc: Phase 13 complete, transitioned to Phase 14
state_head: f458dc91e42d4f273cde34ebb98bf03855b7bdd7
progress:
  total_phases: 4
  completed_phases: 3
  total_plans: 15
  completed_plans: 15
  percent: 75
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-11-17)

**Core value:** Count, query, and merge k-mers at genome scale within practical memory — fast and lean enough to compete with best-in-class tools (KMC / Jellyfish class), from both the CLI and Python.
**Current focus:** v2.1 milestone close — Phase 14 not executed (D3 NO-GO)

## Current Position

Phase: 14 — Parallel Extraction (NOT EXECUTED — D3 NO-GO)
Current Plan: Not started
Total Plans in Phase: TBD (never planned)
Status: All phases complete (Phase 14 NOT EXECUTED — D3 NO-GO)
Last activity: 2026-11-17 — Phase 13 verified (UAT 3/3) and marked complete

Progress: [████████░░] 75%

## Performance Metrics

**Velocity (v2.0):** 29 plans / 6 phases over 2026-11-12 → 2026-11-14; v1.0: 31 plans / 4 phases (per-plan metrics archived in `milestones/v1.0-phases/`). Post-v1.0 hygiene wave: 10 quick tasks (records in `.planning/quick/`).

**By Phase (v2.1):**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 11. Merge Characterization & Harness Prep | 8/8 | 8 | ~29 min |
| 12. Full-Scale Merge Verdict | 4/4 | 4 | ~1h 51min |
| 13. Producer Attribution Research | 3/3 | 3 | ~52 min |
| 14. Parallel Extraction (conditional — D3) | NOT EXECUTED | — | — |

**Recent Trend:**
- v2.1 executable scope complete at Phase 13; v2.0 baseline ~31 min/plan (see `milestones/v2.0-ROADMAP.md`)

*Updated after each plan completion*
**Per-Plan Metrics:**

| Plan | Duration | Tasks | Files |
|------|----------|-------|-------|
| Phase 11 P01 | 18min | 3 tasks | 5 files |
| Phase 11 P02 | 17min | 2 tasks | 2 files |
| Phase 11 P03 | 6min | 2 tasks | 5 files |
| Phase 11 P08 | 10min | 2 tasks | 6 files |
| Phase 11 P04 | 15 min | 3 tasks | 3 files |
| Phase 11 P05 | 63min | 3 tasks | 1 files |
| Phase 11 P06 | 80min | 3 tasks | 2 files |
| Phase 11 P07 | 24min | 3 tasks | 5 files |
| Phase 12 P01 | 22 min | 1 tasks | 2 files |
| Phase 12 P04 | 45 min | 2 tasks | 2 files |
| Phase 12 P02 | 6h 47min | 3 tasks | 10 files |
| Phase 12 P03 | 12min | 2 tasks | 2 files |
| Phase 13 P01 | 14 min | 3 tasks | 4 files |
| Phase 13 P02 | 2h 19min | 2 tasks | 1 files |
| Phase 13 P03 | 4min | 2 tasks | 7 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table. Recent decisions affecting current work:

- [v2.1 scope, 2026-11-16]: merge verdict + producer research + hygiene; memory bar is "below jellyfish" (already met at both k); MINIM-01..03 permanently descoped; KMC3 dropped; jellyfish is the sole comparator
- [v2.1 roadmap, 2026-11-16]: Phases 11-14 continue v2.0 numbering (v2.0's Phase 11 never created); only two hard dependencies — 13→14 (D3 gate) and 12→14 (provenance stability); 13 is independent and may overlap 11-12 (measurement-only); hygiene is woven into Phase 11 with HYG-01 pulled forward before the merge verdict
- [D3 pattern reused]: Phase 14 executes ONLY if Phase 13's predicted-win memo says GO; PEXT-03/PEXT-04 are conditional requirements
- [v2.0 D3, 2026-11-14]: the prior Phase 11 (MINIM) did NOT execute — Stage A hit parity and memory was below jellyfish; MINIM descoped outright on 2026-11-16
- [Phase 11]: 11-01 renderer scope: merge row gains jellyfish-merge deltas via _arm_row merge_base param; merge-t1/jellyfish-merge table rows deferred to Phase 12 renderer work
- [Phase 11]: 11-01: --skip-merge excludes all three merge arms symmetrically; jellyfish-count-B from cfg_b with byte-identical -m/-s/-C per D-01
- [Phase 11]: prepare_inputs reconcile_anchors(totals_by_k, anchors=None, ks=None) is the single anchor enforcement point: build calls ks=(k,) per k mid-build (abort before next k / -s derivation); default full-set shape raises on missing k
- [Phase 11]: prepare_inputs DEFAULT_RUSTKMER is REPO_ROOT-resolved absolute (stage runs from any cwd); jf stage re-verifies recorded .rkdb identity + source fingerprints before building .jf inputs (the -s plan depends on those Distinct values)
- [Phase 11]: hash_size_plan carries slots/occupancy computed by the stage (jellyfish 2.3.1 info reports only command/where/when/canonical, probed 2026-11-16); empty .rkdb stats exit-1 normalized into the zero-count abort (MBENCH-01/empty)
- [Phase 11]: [11-03]: benchmark-report.md SUPERSEDED banner is the single acknowledged generated-file exception (re-render from v1.0 JSONs drops it); renderer-narrative debt (bench.py halt note :1981-1990, CRR2044018 block :2040-2045 post-11-01 anchors) owned by the post-Phase-12 rewrite — protects old-JSON re-render byte-identity per research Open Question 4; recorded in 11-HYGIENE-RECORD.md
- [Phase 11]: [11-03]: dataset description corrected to six single-member gzip parts (~2.79 GB each, ~16.7 GB total), pinned pair part_001+part_006 unchanged; HYG-04: WARNING-2 assigned to the 11-07 same-touch, backlog 999.1-999.3 not triggered (tracked, non-gate-blocking) — D-05/D-06 factual fixes only; HYG-04 opportunistic rule
- [Phase 11]: [11-08]: Phase 7 draft VALIDATION.md confirmed in place via the workflow's State A audit (draft -> validated, Wave 0 verified delivered) rather than re-issued; 05/06/08 reconstructed grounding on the archived 2026-11-14 re-verification reports; security records keep plan-time dispositions (09 T-9-07 accepted low / IN-03 info-only; 10 T-10-SC reserved) — 8 Info findings NOT re-opened
- [Phase 11]: 11-04: merge parity gate wired as pre-gate (assert_merge_parity) + deep verdict gate (dump_vs_dump_equal), both before results acceptance, guarded on the jellyfish-merge arm
- [Phase 11]: 11-04: comparator sorts in-process with Python str ordering (byte-identical to LC_ALL=C over the ASCII dump alphabet) instead of shelling out to sort; dumps go via workdir files (rustkmer dump -o / jellyfish dump -c stdout)
- [Phase 11]: 11-04: live slice proof head-provisions 200k reads from the first sorted parts (functional gate proof only); the pinned part_001+part_006 pair and union anchors bind full-scale runs through the prepare manifest
- [Phase 11]: 11-04: MBENCH-02 left unmarked in REQUIREMENTS.md — shared with 11-07 which has no SUMMARY yet (shared-ID gate)
- [Phase 11]: 11-05: per-part -s approved as derived via plan auto_select option-a (AUTO mode): 1G@k21 occ 0.619, 2G@k31 occ 0.388; A4 closed — derived -s, not 10G-everywhere; fairness via k-pair hash-size equality + recorded occupancy
- [Phase 11]: 11-05: artifact budget approved on measured reality — 86.74 GiB actual vs D-01 ~70 GiB estimate (superseded by measurement, inside the recorded 85.8-109.8 GiB projection band); merge-output occupancy pre-computed for 11-07 floor: k21 0.836, k31 0.534
- [Phase 11]: 11-06: rung gates execute per PARITY-GATE.md before record acceptance; the deep dump-vs-dump leg runs the written spec's streaming form at ladder scale (measured 318.5M/373.0M lines per side — the in-process variant would need ~120-150 GB heap), implemented in merge_characterize.py with bench.py untouched
- [Phase 11]: 11-06: ladder slopes all linear (40/10 wall-per-entry ratios 1.06-1.37, under the 2x flag) — jellyfish 8.97e-8/1.008e-7 s/entry k=21/31, rustkmer 6.67e-8/7.41e-8; extrapolated full-scale merge walls rustkmer 53.8/73.4 s, jellyfish 77.3/105.5 s with the MBENCH-04 backstop caveat — the Phase 12 scheduling input and the 11-07 D-10 transient term
- [Phase 11]: [11-07]: disk floor DERIVED = 136 GiB (inputs 93,135,484,166 B + largest ladder-extrapolated single-arm transient 22,927,072,000 B) x 1.25 margin; replaces stale 150 (count-era -s 10G regime); import-time tripwire pins the literal to derive_disk_floor(recorded inputs)
- [Phase 11]: [11-07]: D-11/D-12 live — every under-floor path states the GiB shortfall (exit-3 block; --disk-floor-override prints-and-continues), ensure_disk_headroom runs before each measured rep of any comparison protocol; slice/rehearsal runs pass scaled budgets explicitly
- [Phase 11]: [11-07]: dress rehearsal green — 4 staged slice runs (A 50k×2 gate-proof / B 200k×3 full protocol, k=21+31), seven arms counterbalanced, parity + dump-vs-dump green pre-acceptance; B-k21 exactly reproduces 11-04 proof (29,730,885/51,936,393); RSS context-only, t1 = 2-thread pool contract at N=1 (A6)
- [Phase 11]: [11-07]: HYG-04 WARNING-2 closed in the same README touch — 'requested + 1' replaced by exactly-2-at-N=1 / 2N+1-at-N>1 with tests/thread_pool_size_tests.rs cited; 999.1-999.3 remain not-triggered
- [Phase 12]: 12-01: verdict stage publishes exactly one carrier doc (12-VERDICT.json); a measured NO publishes both per-k blocks with exit 1/INVEST
- [Phase 12]: 12-01: results-doc arms carry per-arm provenance + unique_kmers/total_kmers/output_bytes so rates render mechanically; 12-04 timed docs must match this arm contract
- [Phase 12]: 12-01: renderer refuses any ladder doc whose caveat != merge_characterize.FULL_SCALE_CAVEAT (docs not written by this harness cannot be rendered)
- [Phase 12]: 12-04: session-stage seams default to pinned constants but are injectable (artifacts_dir/scratch/source_paths/measured-run guards) — production byte-identical, unit tests hermetic (a fixture revalidate honoring the hardcoded real dir hashed 86.74 GiB per test)
- [Phase 12]: 12-04: results docs carry validator-clean provenance (rustkmer release block) plus comparator_provenance {rustkmer, jellyfish} — the plan's raw two-key provenance mapping would fail write_doc's validate_provenance
- [Phase 12]: 12-04: session-budget entries read merge_characterize.UNION_DISTINCT_ANCHORS (the constant that wrote 11-LADDER-RESULTS.json full_scale_entries); budget on recorded values = 282 GiB (inputs 87 + parity 173 + timed 22)
- [Phase 12]: 12-04: Leg-2 recount Total is asserted EXACT vs the union anchor before the per-k-mer diff; timed arms carry output_sha256 from the final rep's actual output bytes
- [Phase 12]: 12-02 full-scale session verdict NO-INVEST (exit 0): rustkmer merge median walls 63.34s (k=21) / 82.86s (k=31) beat jellyfish merge 88.44s / 114.70s — parity green at both k before any timed rep, exactly 3 counterbalanced reps per arm (D-02)
- [Phase 12]: 12-02 findings recorded never smoothed: predicted-vs-measured +8.7..17.6% on all four rows (warmups landed within -6.4..+3.1%, suggesting a uniform timed-window host-state factor); k=31 merge-arm cv_warning (rep-0 101.51s); honest cache_state unavailable + route not-reported on all 18 reps
- [Phase 12]: 12-02 Rule 1 fix: round-0 source-fingerprint lookup now tokenizes the dotted file name (Path.stem of CRR1936095_r1.part_001.fq.gz strips only .gz so suffix checks missed it); regression test added, suite 73 passed, fix committed before the session ran
- [Phase 12]: 12-03: D-04 executed as one full-file rewrite of docs/benchmark-report.md bound to 12-MERGE-REPORT.md by the greppability gate; only the seven pinned context decimals (2.79/16.7/86.74/144.69/147.08/43.97/68.52) outside it, each labeled context
- [Phase 12]: 12-03: D-03 deletion order held (evidence commits -> docs rewrite df81ba1 -> cleanup record 7c608e9); explicit-path deletion of the 8 artifacts (86.74 GiB), manifest.json retained, rebuild via prepare_inputs.py build
- [Phase 13]: Phase-13 driver implements D-09 attribution exactly as researched (delta-corrected inflate unclamped; route_send/output_stage residuals) and reduces probe nanos through the input-type-scoped pair-sum median, never bench.reduce_arm
- [Phase 13]: A3/A4 anomaly criteria drive bounds mode; the conservative (derated) end remains the D-05 bar input in both modes
- [Phase 13]: Materialized probe crates share one scratch CARGO_TARGET_DIR and are built only after seeding + sha256-verifying their committed lock fixtures
- [Phase 13]: 13-02: fresh arm-A base measured 158.29 s k=21 / 177.63 s k=31 (D-10 re-measure); v2.0 walls remain disclosed-fingerprint corroboration only
- [Phase 13]: 13-02: D-09 attribution (unclamped): inflate 26.25/21.02 s, parse_extract 20.96/20.85 s, route_send 91.80/92.99 s, output_stage 22.39/41.84 s; read-delta corrections -1.13/-1.29 s recorded negative as measured
- [Phase 13]: 13-02: D-05 decision NO-GO — derated predicted improvement 9.62% (k=21) below the 10.0 bar, 10.80% (k=31) above; both-k conjunction fails on k=21; both model modes point (A3/A4 not tripped)
- [Phase 13]: 13-02: plain inputs measured 4.57x gzip (76.29 GB vs 16.71 GB); cache_state and thermal unavailable on every rep (honest labels); per-rep .rkdb outputs deleted
- [Phase 13]: D3 gate memo rendered deterministically from 13-ATTRIBUTION.json: DECISION NO-GO — conservative derated predicted improvement 9.6235% at k=21 / 10.7965% at k=31 against the pre-registered 10.0% both-k conjunction; byte-identical re-render proof committed
- [Phase 13]: Live-render seam fixed (c797bfe): the probe-vs-CLI topology methodology note now renders in both memo branches, committed before the memo so the memo is reproducible from the committed driver
- [Phase 13]: D-04 lifecycle closed after the memo commit: six CRR1936095-plain parts (76,290,905,669 B) and /tmp/phase13-probe-scratch deleted by explicit path; gzip source root untouched; scratch_cleaned true
- [Phase 13 UAT]: 3/3 pass (agent-audited at user request); combined parse_extract granularity accepted; api-coverage verify:pre gate resolved by 13-COVERAGE.md no-external-API declaration

### Pending Todos

None yet.

### Blockers/Concerns

- [Environment, OPEN] `scripts/bench/tests/test_verify_threads.py::TestNegativeControls::test_pre_engine_n_plus_one_stub_is_measured_red` is a pre-existing ~50% macOS `sample`-race flake. A shared `target/` across git worktrees can bake a deleted `CARGO_MANIFEST_DIR` into test binaries — purge stale artifacts before trusting a red result.
- [Carried, OPEN] IN-06/07/09 (Phase-04 review findings) deferred per triage 261111-spz; backlog 999.1-999.3 opportunistic — now HYG-04 in Phase 11.
- [Phase 9, OPEN] 8 Info findings in `09-REVIEW.md` (info only); SECURITY.md for Phases 9/10 is now HYG-03 (Phase 11).
- [Carried W1, OPEN] push dev so local commits get remote CI validation.
- [v2.1 planning note] MBENCH-02's gate is built in Phase 11 (written spec + slice-scale deep gate); its full-scale execution (per-k-mer deep validation) runs inside Phase 12's protocol — parity before timing binds both phases.
- [v2.1 research gap] jellyfish merge runtime/memory at 20-90 GiB is extrapolated until Phase 11's intermediate-scale characterization; disk pre-flight 150-400 GiB is an estimate — re-derive from v2.0 measured DB sizes and expect to raise `--disk-floor-gb`.
- Pre-existing (not 11-01): test_phase10_verdict.py reads archived .planning/phases/10-benchmark-verdict/ paths moved to .planning/milestones/v2.0-phases/ by 97c497c — 3 full-suite tests red; path retarget needed (see 11-01 deferred-items.md)
- [Resolved 2026-11-17] The path-retarget line above was fixed by quick task 261117-ala (commits 20caf42 + 89b6776) — full suite green (644 tests, exit 0); README WR-04 rehearsal commands also fixed.

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 261117-ala | Retarget 3 test_phase10_verdict.py archived-path failures to .planning/milestones/v2.0-phases/ + fix WR-04 README rehearsal command flags | 2026-11-17 | 89b6776 | [261117-ala-retarget-3-test-phase10-verdict-py-archi](./quick/261117-ala-retarget-3-test-phase10-verdict-py-archi/) |

## Deferred Items

Items acknowledged and carried forward, most recent first:

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| Review findings | IN-06/07/09 (Phase-04 harness/test code) | Deferred (triaged 261111-spz) | 2026-11-11 |
| Backlog | 999.1 pyo3 build.rs link args; 999.2 stale site-packages shadowing; 999.3 stale sweep claim | Opportunistic in v2.1 (HYG-04, Phase 11) | 2026-10-09 |
| Review findings | 8 Info findings in `09-REVIEW.md` (Phase 9) | Info-only, tracked | 2026-11-14 |
| Descoped | MINIM-01..03; KMC3 comparison (BENCH-V2-01) | Permanently descoped (user decision) | 2026-11-16 |
| Deferred to v2.2+ | MBF-01 (merge flag sweep, post-INVEST); MBF-02 (N-way/r1+r2); PEXT-05 (extractor refinements) | Post-verdict follow-ons | 2026-11-16 |

## Session Continuity

Last session: 2026-11-17T15:30:17.153Z
Stopped at: Phase 13 complete — Phase 14 not executed (D3 NO-GO); v2.1 ready to close
Resume file: None
