# Phase 11: Merge Characterization & Harness Prep - Context

**Gathered:** 2026-11-16
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 11 makes the merge comparison safe to run before any multi-hour full-scale session is spent. It delivers: the extended harness (jellyfish per-part count artifacts + `jellyfish merge` command arm + like-for-like `rustkmer merge --num-threads 1` arm under the existing counterbalanced protocol — MBENCH-01); the three-way parity gate defined in writing and proven at slice scale via a full-protocol dress rehearsal (MBENCH-02's gate portion — its full-scale execution belongs to Phase 12); the CI degradation rung for the merge arm inside the existing results schema (MBENCH-05); intermediate-scale jellyfish merge characterization; and the pulled-forward hygiene items (HYG-01 stale `docs/benchmark-report.md`, HYG-02 Nyquist for Phases 5–8, HYG-03 SECURITY.md for Phases 9/10, HYG-04 opportunistic backlog).

**No Rust code changes in this phase** — harness (Python), docs, and hygiene workflows only. New capabilities are out of scope; everything here clarifies HOW to run what the roadmap already scoped.

</domain>

<decisions>
## Implementation Decisions

### Input Artifacts (full-scale merge inputs)
- **D-01:** All 8 full-scale merge input artifacts (part_001/part_006 × `.rkdb`/`.jf` × k=21/31, ~70 GiB total) are **pre-built in Phase 11**, not at Phase 12 round 0. Rationale: the dress rehearsal and characterization then validate the real fingerprint/Total-revalidation path, and Phase 12 starts clean with zero setup risk. Verified 2026-11-16: no v2.0-era `.rkdb`/`.jf` artifacts survive on disk — regeneration is the only option. — **Reversibility:** reversible — artifacts are rebuildable from source data by re-running the prepare stage (~30–90 min).
- **D-02:** Retention: keep all artifacts on disk **until the Phase 12 verdict lands**, then clean up. Do NOT delete `.jf` early (parity-green deletes cost more than ~22 GiB of disk: `.jf` regeneration forces re-running jellyfish merge arms).
- **D-03:** Artifacts live in a **dedicated directory next to the source data, outside the repo** — e.g. `/Users/forrest/Data/data/illumina/CRR1936095-merge-inputs/` (exact name planner's choice). Never inside the repo tree (mis-commit risk).
- **D-04:** Artifacts are built by a **harness built-in stage** (prepare-inputs subcommand or equivalent in `scripts/bench/`) that records sha256 + Total + command-line provenance automatically. No manual fingerprint transcription. Phase 12 round-0 revalidation consumes the same recorded provenance. — **Reversibility:** costly — provenance records feed the Phase 12 round-0 gate and the verdict's methodology block; changing the record format after the fact means re-rendering/re-validating everything downstream of it.

### Stale Report Resolution (HYG-01)
- **D-05:** `docs/benchmark-report.md` gets a **superseded banner now** (pointing to v2.0 milestone evidence in `.planning/milestones/`) + the dataset-description correction (six single-member gzip parts ~16.7 GB, not "two parts ~5.2 GB"); the **full v2.0-based rewrite is deferred until after the Phase 12 merge verdict** so the doc is rewritten once, including merge results (see Deferred).
- **D-06:** Drift sweep breadth: the two named artifacts (`docs/benchmark-report.md`, PROJECT.md dataset description) **plus a grep sweep** of `docs/`, `README.md`, `USER_GUIDE.md`, `PROJECT_SUMMARY.md` for same-class drift (stale dataset description, stale "+420%" cites). Factual fixes only — no document rewrites (a full docs audit is /gsd-docs-update territory, out of scope).

### Characterization Ladder (intermediate-scale)
- **D-07:** **Two-point ladder** (e.g. ~10% and ~40% of part scale) — slope + coarse linearity check is sufficient for Phase 12 scheduling and the disk-floor derivation. The MBENCH-04 predicted-vs-measured check at full scale is the backstop against residual non-linearity.
- **D-08:** Ladder inputs are **real-data slice pairs** via the existing `random_slice.py`/`make_slice.sh` mechanism, each side running the complete prepare→count→merge chain. This also exercises the prepare-inputs stage (D-04) on real data before it matters.
- **D-09:** **Both tools are characterized** on the same slice pairs — `jellyfish merge` AND `rustkmer merge`. This gives MBENCH-04's cost-model check a fitted curve instead of an assumed slope and surfaces rustkmer-side scaling behavior (route switches, spill) before full scale.

### Disk Pre-flight
- **D-10:** The raised disk floor is a **derived formula**: input artifacts + largest single-arm transient (extrapolated from the D-07/D-09 ladder) + safety margin — derived in Phase 11 from measured sizes and written into the bench default (replacing the 150 GiB default sized for count artifacts). Re-derive if inputs change. — **Reversibility:** costly — the floor guards the Phase 12 full-scale session; a mis-derived floor discovered mid-session wastes hours, so the derivation and its inputs are recorded evidence.
- **D-11:** Below the floor → **hard block with the shortfall stated** + an explicit override flag (e.g. `--disk-floor-override`) for deliberate runs. No silent continue.
- **D-12:** Check timing: **full-budget check before round 0** (all arms + transients) + **lightweight re-check before each rep** (catches other processes filling the disk during multi-hour sessions).

### Claude's Discretion
- Dress rehearsal breadth: full protocol at slice scale (all arms, both k) — success criterion 2 already says "full-protocol"; both k is cheap at slice scale.
- Parity-gate written spec: exact document location and format (phase-dir doc vs docs/) — planner picks; the content requirements are fixed by MBENCH-02 (three legs, per-k-mer exact, `total_kmers` definition named per check).
- Characterization results format/location: follow existing evidence-JSON patterns.
- prepare-inputs stage CLI shape and naming.
- Whether a `phase11.py` staged controller is created in this phase or deferred to Phase 12 (ROADMAP marks the controller optional for the Phase 12 session).
- HYG-02/HYG-03 run through the named workflows (`/gsd-validate-phase`, `/gsd-secure-phase`) as their requirements state; HYG-04 stays opportunistic per the backlog rule (fix in the same touch when milestone work touches 999.1–999.3 files).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Milestone research (primary input — unusually complete, per ROADMAP)
- `.planning/research/SUMMARY.md` — executive summary, pitfalls 1/2/3/5/7/8 (all mapped to this phase), phase recommendations
- `.planning/research/FEATURES.md` — MERGE-BENCH must-have/should-have table; arm definitions and input-equivalence rules
- `.planning/research/ARCHITECTURE.md` — harness integration points, file:line-anchored into `bench.py`/`phase10.py`
- `.planning/research/PITFALLS.md` — full pitfall catalog (canonicality silent mixing is Pitfall 1, HIGH)
- `.planning/research/STACK.md` — jellyfish 2.3.1 semantics pinned empirically + source (merge is single-threaded streaming, O(1)-per-input memory ~6.8 MB)

### Requirements & roadmap
- `.planning/REQUIREMENTS.md` — MBENCH-01/02/05, HYG-01..04 definitions and mapping notes
- `.planning/ROADMAP.md` §Phase 11 — success criteria 1–5 + the phase Note (artifact decision, disk pre-flight re-derivation, MBENCH-02/12 split)
- `.planning/PROJECT.md` — v2.0 verdict numbers (144.69/147.08 s; MEM references 43.97/68.52 GiB) and guardrails that bind this phase

### Harness code (extension surface)
- `scripts/bench/bench.py` — counterbalanced protocol, round_schedule, parity pre-gate, renderer, disk floor guard, results schema
- `scripts/bench/phase10.py` — staged full-scale controller precedent (0/1/2 exit-code contract)
- `scripts/bench/random_slice.py`, `scripts/bench/make_slice.sh` — slice mechanism for the characterization ladder
- `scripts/bench/output_stage.py` — rotation + cache purge helpers
- `scripts/bench/gen_synthetic.py` — synthetic inputs for the CI degradation rung (MBENCH-05)
- `scripts/bench/README.md` — harness usage; carries WARNING-1/WARNING-2 opportunistic items (Phase 11 touches `scripts/bench/`)

### Hygiene targets (HYG-01)
- `docs/benchmark-report.md` — the stale report (banner target; still headlines v1.0 k=21 "+420%" from the deleted substitute dataset)
- `.planning/PROJECT.md` §Benchmark dataset / §Constraints — dataset description correction target ("two parts ~5.2 GB" → six parts ~16.7 GB, pinned arrangement still part_001+part_006)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `bench.py` protocol machinery: counterbalanced rounds (`round_schedule` generalizes to 6 arms), per-rep honest `cache_state`, medians + CV%, zero-count sanity, fingerprints, schema validation, disk floor guard, count-parity pre-gate — all extended additively, no rewrite
- `phase10.py` staged controller — template for dress-rehearsal orchestration and (optional) the Phase 12 session controller
- Existing synthetic two-part merge arm — the CI degradation rung extends it (MBENCH-05), never a second results schema
- Known jellyfish facts from pinned-binary experiments: `jellyfish merge` merges ≥2 same-hash `.jf` files (hash-size equality enforced — v2.0's single jf-t16 artifact is NOT usable), no `-t`, no `-s` on merge, output size capacity-derived, ~6.8 MB RSS while merging

### Established Patterns
- Provenance on every artifact: sha256 + commit + build profile + command line; honest per-rep `cache_state`
- Parity-before-timing (locked v2.0 precedent) — the merge gate inherits it: three-way, exact per k-mer, executed before any timed round
- The renderer `_arm_row` merge `n/a` special case is load-bearing for old results files — extend, don't remove
- Golden baselines are ground truth, never regenerated (D-10 pattern from testing conventions)
- Nyquist/security hygiene flows through `/gsd-validate-phase` and `/gsd-secure-phase` — not hand-rolled

### Integration Points
- `BenchmarkConfig` drives both tools' command lines — canonicality (-C) pinned in one config (Pitfall 1 mitigation)
- Input fingerprint + Total revalidation gates round 0 (research Pitfall 8)
- Disk floor guard in `bench.py` — re-derived and raised per D-10/D-11/D-12
- Dataset root: `/Users/forrest/Data/data/illumina/CRR1936095_r1.fq.gz.split/` (six single-member gzip parts, ~2.6 GB each); pinned merge arrangement part_001 + part_006
- New artifacts root: `/Users/forrest/Data/data/illumina/CRR1936095-merge-inputs/` (D-03; exact name planner's choice)
- Known harness flakes/concerns carried in STATE.md: the `test_verify_threads.py` macOS `sample`-race flake (~50%, pre-existing) — purge stale `target/` artifacts before trusting a red result

</code_context>

<specifics>
## Specific Ideas

- Artifact regeneration is forced by reality (verified on disk 2026-11-16) — the discussion framed "reuse vs regenerate" and resolved to regenerate-in-Phase-11 via a harness stage.
- Retention is explicitly tied to the Phase 12 verdict lifecycle: verdict lands → cleanup. Disk budget arithmetic (70 GiB artifacts + 150–400 GiB transients vs 345 GiB free) is the reason the disk pre-flight got its own decisions.
- The characterization doubles as the first live exercise of the prepare-inputs stage and the new arms — deliberately, so harness bugs surface at slice/intermediate scale, not mid-session.

</specifics>

<deferred>
## Deferred Ideas

- **Full v2.0-based rewrite of `docs/benchmark-report.md`** including merge-verdict sections — after the Phase 12 verdict lands, so the doc is rewritten once with complete current data (D-05). Needs a home at v2.1 close (candidate: Phase 12 wrap-up task or a post-verdict quick task).
- (Carried from milestone scope, unchanged: MBF-01 flag sweep, MBF-02 N-way/r1+r2, PEXT-05 — post-verdict v2.2+ items, not this phase.)

</deferred>

---

*Phase: 11-Merge Characterization & Harness Prep*
*Context gathered: 2026-11-16*
