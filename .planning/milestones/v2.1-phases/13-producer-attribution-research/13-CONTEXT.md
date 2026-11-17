# Phase 13: Producer Attribution Research - Context

**Gathered:** 2026-11-17
**Updated:** 2026-11-17 (second `--auto` pass — folds the research open questions and the plan-time pre-registrations into the locked decision set; D-01..D-04 preserved unchanged in intent)
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 13 answers one question with full-scale measurements on the SHIPPED engine: where does the producer wall actually go — inflate vs parse vs extract vs route-send — and does parallel extraction's predicted win clear the D3 bar? Deliverables: a stage-attribution table at BOTH k from fingerprinted builds (arms A-D: stock gzip / pre-decompressed / stage sub-timers / null consumer, plus a pure-read control — PEXT-01), and a predicted-win model naming BOTH ceilings (parallelizable share × worker-side scaling) with every input number cited to a named full-scale source run, recorded as a go/no-go memo that either triggers Phase 14 or closes PEXT with evidence (PEXT-02).

**Measurement-only phase — no Rust code changes land.** The engine binary stays fingerprint-stable (Phase 12's verdict is already recorded, so provenance stability is no longer a sequencing constraint). Slice-scale numbers and pre-Phase-7 profiles never feed the gate decision. Expected outcome per current evidence: inflate ~13% (below the ~20% zlib-rs gate), parse+extraction ~85%+ — zero-dependency extraction parallelization is the likely lever (ROADMAP Note).

**Pre-registration discipline:** the numeric D3 bar and its modeling constants are fixed BEFORE any full-scale measurement runs; the memo applies the pre-registered bar rather than choosing a threshold after seeing the data (D-05).

</domain>

<decisions>
## Implementation Decisions

### Measurement Vehicle
- **D-01:** Arms A-D are driven by a **harness-built driver script** (the `merge_characterize.py` pattern: stdlib-only, provenance on every run, evidence JSON per arm-k, fail-loud parsing) — not hand-run CLI invocations and not a Rust-side instrumentation addition. The headline numbers come from the plain-vs-gzip differential + pure-read control; `--features profiling` stage sub-timers (arm C) are the cross-check, not the headline source. Both k for every arm. — **Reversibility:** reversible — a code artifact + evidence JSONs.

### D3 Gate Memo
- **D-02:** The go/no-go decision is recorded as a **committed memo in the phase directory** (evidence-JSON + markdown pattern, e.g. `13-GATE-MEMO.md` + `13-ATTRIBUTION.json`): the memo names both ceilings, cites every input number to a named full-scale source run, and states GO (Phase 14 executes) or NO-GO (PEXT-03/04 remain unexecuted by recorded decision). ROADMAP §Phase 14 carries the conditional annotation pointing at the memo. The memo is a **deterministic render** of the evidence JSON with a byte-identical re-render proof; both outcomes exit 0 (a recorded decision is a valid result, infrastructure failures exit 2). — **Reversibility:** costly — the memo is the gate input for Phase 14's existence; changing it after Phase 14 starts invalidates the conditional phase, so the derivation and its inputs are recorded evidence.

### Full-Scale Input Sources
- **D-03:** **Fingerprint-gated reuse of v2.0 walls:** first compare the current release binary's sha256 against v2.0's recorded fingerprint — if identical, v2.0's measured walls (CLI 144.69 s k=21 / 147.08 s k=31; Python 165.05 s / 178.22 s) are cited directly as the base; if it differs, the driver re-measures the base walls fresh at full scale before any differential math. PEXT-01's fingerprinted-builds requirement applies to every run either way. — **Reversibility:** reversible — the gate is deterministic on the fingerprint. *(Live outcome recorded in D-10.)*

### Session Scale & Input Lifecycle
- **D-04:** **Each arm-k runs 3 reps** (attribution is a ratio measurement; 3 reps give a median + honest spread without another multi-hour session). The plain (pre-decompressed) FASTQ inputs are **decompressed once into a dedicated directory outside the repo** (data-adjacent, e.g. `/Users/forrest/Data/data/illumina/CRR1936095-plain/`, ~60 GB for six parts), provenance-recorded like every artifact, and **deleted after the memo lands** (the memo cites the recorded evidence, not the bytes). Disk arithmetic is checked before decompression against current free space. — **Reversibility:** reversible — plain inputs are regenerable from the gzip parts.

### D3 Bar & Decision Semantics
- **D-05:** The D3 gate applies a **pre-registered numeric bar: predicted full-wall improvement ≥ 10.0%** on the **conservative (efficiency-derated) model**, with `>=` semantics (exactly 10.0% is GO), applied at **BOTH k** (a conjunction — either k below the bar is NO-GO). The modeled constants are pre-registered too: **16 extractor threads** (the decision-relevant count, matching v2.0's CLI arms) and **derated extractor efficiency E = 0.5**; the idealized E=M bound is reported alongside but never used for the bar test. The bar test consumes the conservative pair. — **Reversibility:** costly — pre-registration is the gate's credibility; changing the threshold after seeing the attribution table invalidates the memo and the Phase 14 contract, so a change requires a recorded re-pre-registration before any measurement.

### Decision Surface
- **D-06:** The predicted-win model and the gate decision are scoped to the **CLI count wall** (the primary decision axis). The Python-surface walls (165.05 s k=21 / 178.22 s k=31) are cited as **context only**, with their module fingerprint and the binary-fingerprint caveat stated; the memo's headline is not dual-surface. — **Reversibility:** reversible — a scoping statement in the memo; adding a Python arm later is a new measurement, not a re-decision.

### Decompression & Context Matrix Scope
- **D-07:** **Decompress all six gzip parts** (not just the pinned pair). The **pinned pair** (`part_001` + `part_006`) feeds the gate arms; the **four non-pinned parts feed a per-part context matrix** — arm C × gzip+plain × both k × 1 rep — recorded with `context=true` / `excluded=true` so `build_attribution` and `derive_gate_decision` structurally cannot consume it. Per-part spread is Phase-14 sizing context, never a gate input. — **Reversibility:** reversible — extra plain inputs are regenerable; the context matrix is additive evidence.

### Arm A/B Workload Shape
- **D-08:** Stock arms A/B **write a `.rkdb` output to scratch (`-o`)**, deleted immediately after each rep's stats are recorded. An output-less run is not comparable to the v2.0 walls it corroborates (v2.0 passed `-o`, so its wall includes sort+write). — **Reversibility:** reversible — one flag in the arm builder; the fresh base is simply re-measured if the shape changes.

### Attribution Composition
- **D-09:** The attribution table names **`inflate_s`, `parse_extract_s`, `route_send_s`, and `output_stage_s`**, and records both the **raw A−B delta** and the **read-delta correction** (`read_gz − read_plain`) with the sign preserved unclamped — a zero or negative corrected inflate share is recorded exactly as measured, never clamped positive or rounded away. The predicted full wall is `max(parallelizable floor, worker floor) + output_stage_s`, where the parallelizable floor uses the derated AND idealized extractor-efficiency bounds and the worker floor comes from aggregate arm-C `busy_nanos`. — **Reversibility:** reversible — pure-function arithmetic over recorded runs; the evidence JSON keeps the raw terms so the table can be re-derived.

### Fresh-Base Branch Outcome
- **D-10:** The **current release binary sha256 (`4539b893e8ece53bf2faa417f94a4a64d3e3d6c89f1ff94db38c21fafd6d023b`) differs from v2.0's recorded fingerprint (`8f38d20c2e3dc77dfc0ef80c9a2475613da1aa7ad131bd240d5ec74fc87c3d23`)**, so the D-03 gate branches to **`re-measure`**: arm A's own fresh medians are the **only** decision denominator. v2.0's walls appear in the memo only as disclosed-fingerprint corroboration, and no memo percentage may use a v2.0 wall as its denominator while the fingerprint mismatch stands. The binary must be rebuilt clean from HEAD before the gate computation, with `git_dirty: false` asserted and recorded. — **Reversibility:** reversible — the branch is deterministic on the fingerprint; a matching future binary would flip it back to `cite`.

### Carried Constraints (locked, not re-decided)
- No Rust changes land in this phase; measurement-only (binary fingerprint stability).
- Full scale only — no slice-scale number feeds the gate (PEXT-01). Fixture-scale `--rehearsal` proves the chain only; every rehearsal record carries `scale='rehearsal'` and is structurally invisible to memo derivation.
- The six independent gzip parts give a producer-per-file topology ×6 — the sizing model notes this as Phase 14's spread surface if GO.
- Provenance on every run: sha256 of binary + inputs, command line, honest cache_state (established pattern); counterbalanced arm ordering, per-rep cooldown, thermal sample, crash-safe incremental evidence writes.
- The zlib-rs feature decision is NOT made in this phase: the memo records the measured inflate share; the switch belongs to Phase 14 planning and only if inflate measures ≥ ~20% of producer wall.

### Claude's Discretion
- Driver script CLI shape/name and evidence-JSON schema (follow merge_characterize.py + phase11.py evidence patterns; `phase13.py` naming lineage is fine).
- Stage sub-timer invocation details for arm C (profiling feature flags, output capture).
- Probe materialization details: the committed `examples/engine_probe.rs` is k=21-hardcoded and prints JSON; arm C at k=31 needs a materialized k-from-argv variant, and arm D needs a null-consumer probe — both built in /tmp scratch with a `refuse_repo_root` guard (never committed).
- Null-consumer construction (arm D) — minimal-work consumer that isolates read+inflate cost.
- Exact memo structure (both ceilings, arithmetic, citation table) within D-02's deterministic-render contract.
- Cooldown/thermal/incremental-write mechanics inside the measure stage.

### Folded Todos
(None — `todo.match-phase` returned 0 matches.)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Roadmap & requirements
- `.planning/ROADMAP.md` §Phase 13 — goal, success criteria, arms A-D, expected outcome Note; §Phase 14 — the conditional D3 contract the memo gates
- `.planning/REQUIREMENTS.md` — PEXT-01/PEXT-02 definitions + mapping notes
- `.planning/PROJECT.md` — v2.0 measured walls (144.69/147.08 s CLI; 165.05/178.22 s Python) + memory references (43.97/68.52 GiB) the model cites

### Phase 13 planning artifacts (this pass's direct inputs)
- `.planning/phases/13-producer-attribution-research/13-RESEARCH.md` — measurement design, attribution arithmetic, assumptions A1-A5, Open Questions 1-4 (resolved by D-05..D-10)
- `.planning/phases/13-producer-attribution-research/13-VALIDATION.md` — test map, Wave-0 requirements, sampling rate
- `.planning/phases/13-producer-attribution-research/13-PATTERNS.md` — file-by-file analog map (`phase13.py`, probes, tests, evidence JSON, memo)
- `.planning/phases/13-producer-attribution-research/13-01-PLAN.md` — driver tracer + pre-registered constants (`D3_BAR_FULL_WALL_IMPROVEMENT_PCT = 10.0`, `EXTRACTOR_COUNT = 16`, `EXTRACTOR_EFFICIENCY_DERATED = 0.5`)
- `.planning/phases/13-producer-attribution-research/13-02-PLAN.md` — live full-scale session matrix + evidence doc
- `.planning/phases/13-producer-attribution-research/13-03-PLAN.md` — memo render, ROADMAP annotation, input lifecycle

### Milestone research (the measurement design)
- `.planning/research/SUMMARY.md` — producer attribution recommendations + pitfalls mapping
- `.planning/research/FEATURES.md` — PEXT arm definitions (stock / pre-decompressed / stage sub-timers / null consumer) + sizing model
- `.planning/research/PITFALLS.md` — slice-number discipline (Pitfall 14), cache-purge honesty, attribution confounds
- `.planning/research/ARCHITECTURE.md` — producer pipeline stages + `--features profiling` diagnostics locations (file:line)

### Provenance & patterns from prior phases
- `.planning/phases/12-full-scale-merge-verdict/12-CONTEXT.md` — locked decision patterns (fingerprint-gating, evidence lifecycle, wrap-up cleanup, fresh-base discipline)
- `.planning/phases/11-merge-characterization-harness-prep/11-PREPARE-RECORD.md` — source fingerprint records (part_001/part_006 + all six parts) the fingerprint comparison consumes
- `scripts/bench/merge_characterize.py` — the driver-script pattern (stdlib-only, provenance, evidence JSON, fail-loud)
- `scripts/bench/phase11.py` — evidence-doc write pattern (write_doc/validate_provenance), byte-identical render proof, exit-code contract precedent
- `examples/engine_probe.rs` — the committed k=21 profiling probe (JSON output: wall/producer/per-worker busy nanos); template for the materialized k=31 and null-consumer probes

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `merge_characterize.py` — driver-script template: seeded provisioning, chain runner, measured_run with /usr/bin/time, evidence JSON emission
- `phase11.py` — evidence-doc write pattern, byte-identical render proof, exit-code contract, provenance validation
- `--features profiling` diagnostics + `examples/engine_probe.rs` — stage sub-timers already exist in the Rust binary (ROADMAP: no new instrumentation required); arm C reads them. The committed probe hardcodes k=21, so arm C at k=31 requires a materialized variant.
- Dataset topology — six independent gzip parts (~2.79 GB each, ~16.7 GB total) enable per-part producer spread measurement
- `prepare_inputs.py` provenance/manifest patterns — for recording the plain-inputs decompression step

### Established Patterns
- Fingerprint-gated reuse (12-CONTEXT D-03 analog): compare recorded binary sha256 before citing historical walls — live result: mismatch → `re-measure` (D-10)
- Evidence JSON per measurement + committed markdown synthesis (12-02 session pattern); memo is a pure deterministic projection with a byte-identical re-render proof
- Honest negatives: unavailable purge → `unavailable` cache_state; unreported route → `not-reported`; signs preserved unclamped
- Full-scale-only discipline: slice/rehearsal numbers never feed gate decisions (Pitfall 14); `context=true`/`excluded=true` records are structurally invisible to gate math
- Pre-registration: the bar and modeling constants are asserted in unit tests before any measurement runs

### Integration Points
- Dataset root: `/Users/forrest/Data/data/illumina/CRR1936095_r1.fq.gz.split/` (six gzip parts; part_001 = 2,785,381,389 B, part_006 = 2,785,388,289 B verified on disk 2026-11-17)
- Planned plain-inputs root: `/Users/forrest/Data/data/illumina/CRR1936095-plain/` (D-04/D-07; deleted post-memo)
- Release binary: `target/release/rustkmer` — current sha256 `4539b893…` (≠ v2.0 `8f38d20c…`), rebuilt clean from HEAD and `git_dirty: false` asserted before the gate block
- Disk: ~450 GiB free post-cleanup (12-03 freed 86.74 GiB) — ample for ~60 GB plain inputs + transient outputs
- New code lands only under `scripts/bench/` (`phase13.py`, `tests/test_phase13_driver.py`) plus phase-dir evidence artifacts; `src/`, `pyo3/src/`, `examples/` stay unmodified

</code_context>

<specifics>
## Specific Ideas

- This phase is deliberately cheap relative to Phase 12: arms are single count runs (~145-180 s each), 4 arms × 2 k × 3 reps ≈ 24 runs ≈ 1.5-2 h plus decompression (~15-30 min). The expensive artifact of Phase 12 (parity streaming deep legs) has no analog here.
- The D3 bar exists to prevent an unpromising Phase 14: if inflate is ~13% and parse+extraction ~85%, the honest model probably still says GO on extraction parallelization (zero new dependencies) — but the memo must derive that from cited numbers, not from the ROADMAP's expectation note. With D-05's 10.0% derated both-k bar, the expected evidence points to GO; a NO-GO is still a first-class recorded outcome.
- If NO-GO, PEXT-03/04 stay unexecuted BY RECORDED DECISION — that is a first-class outcome, not a failure. The memo carries revisit conditions.
- Pre-registration is load-bearing: the bar (10.0), the derating (0.5), and the extractor count (16) are constants asserted in unit tests, and the decision function consumes the derated bound — never a post-hoc threshold.

</specifics>

<deferred>
## Deferred Ideas

- zlib-rs feature switch — fires only if arm-C/attribution measured inflate ≥ ~20% of producer wall (ROADMAP Note; separate decision at Phase 14 planning if it ever fires).
- Per-part attribution ×6 as a headline (vs excluded context rows) — resolved: context only (D-07).
- Producer-per-file parallel topology design — Phase 14 territory if GO.

</deferred>

---

*Phase: 13-Producer Attribution Research*
*Context gathered: 2026-11-17; updated 2026-11-17 (second `--auto` pass)*
