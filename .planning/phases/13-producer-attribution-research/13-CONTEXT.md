# Phase 13: Producer Attribution Research - Context

**Gathered:** 2026-11-17
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 13 answers one question with full-scale measurements on the SHIPPED engine: where does the producer wall actually go — inflate vs parse vs extract vs route-send — and does parallel extraction's predicted win clear the D3 bar? Deliverables: a stage-attribution table at BOTH k from fingerprinted builds (arms A-D: stock gzip / pre-decompressed / stage sub-timers / null consumer, plus a pure-read control — PEXT-01), and a predicted-win model naming BOTH ceilings (parallelizable share × worker-side scaling) with every input number cited to a named full-scale source run, recorded as a go/no-go memo that either triggers Phase 14 or closes PEXT with evidence (PEXT-02).

**Measurement-only phase — no Rust code changes land.** The engine binary stays fingerprint-stable (Phase 12's verdict is already recorded, so provenance stability is no longer a sequencing constraint). Slice-scale numbers and pre-Phase-7 profiles never feed the gate decision. Expected outcome per current evidence: inflate ~13% (below the ~20% zlib-rs gate), parse+extraction ~85%+ — zero-dependency extraction parallelization is the likely lever (ROADMAP Note).

</domain>

<decisions>
## Implementation Decisions

### Measurement Vehicle
- **D-01:** Arms A-D are driven by a **harness-built driver script** (the `merge_characterize.py` pattern: stdlib-only, provenance on every run, evidence JSON per arm-k, fail-loud parsing) — not hand-run CLI invocations and not a Rust-side instrumentation addition. The headline numbers come from the plain-vs-gzip differential + pure-read control; `--features profiling` stage sub-timers (arm C) are the cross-check, not the headline source. Both k for every arm. — **Reversibility:** reversible — a code artifact + evidence JSONs.

### D3 Gate Memo
- **D-02:** The go/no-go decision is recorded as a **committed memo in the phase directory** (evidence-JSON + markdown pattern, e.g. `13-GATE-MEMO.md` + `13-ATTRIBUTION.json`): the memo names both ceilings, cites every input number to a named full-scale source run, and states GO (Phase 14 executes) or NO-GO (PEXT-03/04 remain unexecuted by recorded decision). ROADMAP §Phase 14 carries the conditional annotation pointing at the memo. — **Reversibility:** costly — the memo is the gate input for Phase 14's existence; changing it after Phase 14 starts invalidates the conditional phase, so the derivation and its inputs are recorded evidence.

### Full-Scale Input Sources
- **D-03:** **Fingerprint-gated reuse of v2.0 walls:** first compare the current release binary's sha256 against v2.0's recorded fingerprint — if identical, v2.0's measured walls (CLI 144.69 s k=21 / 147.08 s k=31; Python 165.05 s / 178.22 s) are cited directly as the base; if it differs, the driver re-measures the base walls fresh at full scale before any differential math. PEXT-01's fingerprinted-builds requirement applies to every run either way. — **Reversibility:** reversible — the gate is deterministic on the fingerprint.

### Session Scale & Input Lifecycle
- **D-04:** **Each arm-k runs 3 reps** (attribution is a ratio measurement; 3 reps give a median + honest spread without another multi-hour session). The plain (pre-decompressed) FASTQ inputs are **decompressed once into a dedicated directory outside the repo** (data-adjacent, e.g. `/Users/forrest/Data/data/illumina/CRR1936095-plain/`, ~60 GB for six parts), provenance-recorded like every artifact, and **deleted after the memo lands** (the memo cites the recorded evidence, not the bytes). Disk arithmetic is checked before decompression against current free space. — **Reversibility:** reversible — plain inputs are regenerable from the gzip parts.

### Carried Constraints (locked, not re-decided)
- No Rust changes land in this phase; measurement-only (binary fingerprint stability).
- Full scale only — no slice-scale number feeds the gate (PEXT-01).
- The six independent gzip parts give a producer-per-file topology ×6 — the sizing model notes this as Phase 14's spread surface if GO.
- Provenance on every run: sha256 of binary + inputs, command line, honest cache_state (established pattern).

### Claude's Discretion
- Driver script CLI shape/name and evidence-JSON schema (follow merge_characterize.py + phase11.py evidence patterns).
- Stage sub-timer invocation details for arm C (profiling feature flags, output capture).
- Null-consumer construction (arm D) — minimal-work consumer that isolates read+inflate cost.
- Exact memo structure (both ceilings, arithmetic, citation table).
- Whether the attribution table records per-part breakdowns as context (the ×6 topology suggests per-part spread is worth recording as context for Phase 14 sizing).

### Folded Todos
(None — todo_count was 0.)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Roadmap & requirements
- `.planning/ROADMAP.md` §Phase 13 — goal, success criteria, arms A-D, expected outcome Note; §Phase 14 — the conditional D3 contract the memo gates
- `.planning/REQUIREMENTS.md` — PEXT-01/PEXT-02 definitions + mapping notes
- `.planning/PROJECT.md` — v2.0 measured walls (144.69/147.08 s CLI; 165.05/178.22 s Python) + memory references (43.97/68.52 GiB) the model cites

### Milestone research (the measurement design)
- `.planning/research/SUMMARY.md` — producer attribution recommendations + pitfalls mapping
- `.planning/research/FEATURES.md` — PEXT arm definitions (stock / pre-decompressed / stage sub-timers / null consumer) + sizing model
- `.planning/research/PITFALLS.md` — slice-number discipline (Pitfall 14), cache-purge honesty, attribution confounds
- `.planning/research/ARCHITECTURE.md` — producer pipeline stages + `--features profiling` diagnostics locations (file:line)

### Provenance & patterns from Phase 12
- `.planning/phases/12-full-scale-merge-verdict/12-CONTEXT.md` — locked decision patterns (fingerprint-gating, evidence lifecycle, wrap-up cleanup)
- `.planning/phases/11-merge-characterization-harness-prep/11-PREPARE-RECORD.md` — source fingerprint records (part_001/part_006 + all six parts) the fingerprint comparison consumes
- `scripts/bench/merge_characterize.py` — the driver-script pattern (stdlib-only, provenance, evidence JSON, fail-loud)
- `scripts/bench/phase11.py` — evidence-doc write pattern (write_doc/validate_provenance), exit-code contract precedent

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `merge_characterize.py` — driver-script template: seeded provisioning, chain runner, measured_run with /usr/bin/time, evidence JSON emission
- `phase11.py` — evidence-doc write pattern, exit-code contract, provenance validation
- `--features profiling` diagnostics — stage sub-timers already exist in the Rust binary (ROADMAP: no new instrumentation required); arm C reads them
- Dataset topology — six independent gzip parts (~2.79 GB each, ~16.7 GB total) enable per-part producer spread measurement
- `prepare_inputs.py` provenance/manifest patterns — for recording the plain-inputs decompression step

### Established Patterns
- Fingerprint-gated reuse (12-CONTEXT D-03 analog): compare recorded binary sha256 before citing historical walls
- Evidence JSON per measurement + committed markdown synthesis (12-02 session pattern)
- Honest negatives: unavailable purge → `unavailable` cache_state; unreported route → `not-reported`
- Full-scale-only discipline: slice numbers never feed gate decisions (Pitfall 14)

### Integration Points
- Dataset root: `/Users/forrest/Data/data/illumina/CRR1936095_r1.fq.gz.split/` (six gzip parts)
- Planned plain-inputs root: `/Users/forrest/Data/data/illumina/CRR1936095-plain/` (D-04; deleted post-memo)
- Release binary: current `target/release/rustkmer` — fingerprint compared against v2.0 recorded values before reuse
- Disk: ~450 GiB free post-cleanup (12-03 freed 86.74 GiB) — ample for ~60 GB plain inputs

</code_context>

<specifics>
## Specific Ideas

- This phase is deliberately cheap relative to Phase 12: arms are single count runs (~145-180 s each), 4 arms × 2 k × 3 reps ≈ 24 runs ≈ 1.5-2 h plus decompression (~15-30 min). The expensive artifact of Phase 12 (parity streaming deep legs) has no analog here.
- The D3 bar exists to prevent an unpromising Phase 14: if inflate is ~13% and parse+extraction ~85%, the honest model probably still says GO on extraction parallelization (zero new dependencies) — but the memo must derive that from cited numbers, not from the ROADMAP's expectation note.
- If NO-GO, PEXT-03/04 stay unexecuted BY RECORDED DECISION — that is a first-class outcome, not a failure.

</specifics>

<deferred>
## Deferred Ideas

- zlib-rs feature switch — fires only if arm-C/attribution measured inflate ≥ ~20% of producer wall (ROADMAP Note; separate decision at Phase 14 planning if it ever fires).
- Per-part attribution ×6 as a headline (vs context) — deferred to planning; the D3 gate needs the aggregate stage table first.
- Producer-per-file parallel topology design — Phase 14 territory if GO.

</deferred>

---

*Phase: 13-Producer Attribution Research*
*Context gathered: 2026-11-17*
