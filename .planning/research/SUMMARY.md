# Project Research Summary

**Project:** rustkmer — Milestone v2.1 "Merge Verdict & Producer Research"
**Domain:** Bioinformatics k-mer tooling — measurement-engineering milestone (benchmark verdict + performance research) against an already-shipped, parity-gated exact-count engine
**Researched:** 2026-11-16
**Confidence:** HIGH overall — the verdict protocol and gates rest on pinned-binary experiments (jellyfish 2.3.1 verified live + against official source) and code-anchored findings (file:line from the current tree); the only LOW-confidence items are web-sourced crate facts that no recommendation hinges on

## Executive Summary

v2.1 is not a feature build — it is two investigation tracks against a system that already ships with paid-for exactness gates. **MERGE-BENCH** runs a full-scale `rustkmer merge` vs `jellyfish merge` benchmark and produces an invest/no-invest verdict (user decisions: jellyfish is the sole comparator; KMC3 descoped because its cutoff-capped counters change SUM semantics; the "below jellyfish" memory bar stands where it always applied — count/extraction, not merge). **PEXT** researches producer-bound parallel extraction for the count engine, with a D3-pattern conditional implementation phase. Experts run milestones like this as measurement engineering: pin the comparator's semantics on the installed binary before trusting any number (done — `jellyfish merge` was verified empirically and against `merge_files.cc`/`mer_heap.hpp` source), define the correctness gate in writing before burning multi-hour counterbalanced reps, and attribute before optimizing.

The agreed build order is **harness extension → full-scale merge verdict → conditional PEXT**, and the measured facts dictate it. `jellyfish merge` is a single-threaded streaming k-way min-heap merge with O(1)-per-input memory — measured **6.8 MB RSS** merging two 240 MB hashes — so the merge decision axes are **wall time (primary) + disk (recorded)**, not RSS; a memory-win framing against this comparator is vacuous. On the producer side, decompression is only **~13% of full-scale producer wall** (~1.2–1.3 GB/s single-threaded inflate, measured locally on a 256 MiB slice; inflate ≈19 s of the 144.69 s full-scale k=21 run) while parse+extraction dominates (~85%+), and **zero-new-dependency parallel extraction is feasible** — `std::thread` + `sync_channel` clones + the existing `PartitionLayout`/`RoutingBuffers`/`for_each_window` machinery cover it. The only conditional stack change is a flate2 `zlib-rs` feature-flag switch, opened only if the profiling gate attributes ≥ ~20% of producer wall to inflate (the ballpark says it will not).

The dominant risk class is **corrupted verdicts, not broken code**. The single most dangerous fact: `jellyfish merge` silently accepts canonicality-mismatched inputs (exit 0, conserved totals, garbage key space — demonstrated on the pinned binary), so aggregate conservation checks structurally cannot catch key-space mixing. The non-negotiable gate is therefore **three-way per-key parity** — `merge(p1,p2) == independent recount of the union == jellyfish merge`, exact per k-mer — executed **before** any timing ("parity before timing" is locked project precedent). Second risk: producer mis-attribution (kernel-wait read as stage cost, stale Phase-5 profiles, slice-scale wall composition now dominated by sort/write) — the PEXT gate is profiling-first at **full scale** with a pure-read control. Third: stale evidence — `docs/benchmark-report.md` still headlines the superseded v1.0 k=21 "+420%" verdict (substitute dataset, since deleted); its drift fix is **pulled forward into Phase 1** so no new artifact can cite it unqualified and the PEXT sizing uses the correct v2.0 baselines (144.69 / 147.08 s, not the stale 505 s).

## Key Findings

### Recommended Stack (PEXT track)

**Headline: zero new dependencies are needed for parallel extraction.** The extraction parallelization attaches entirely to existing, test-pinned machinery; the one candidate stack change is a feature flag on a dependency already pinned.

**Core technologies (unchanged):**
- `std::thread` (+ named `Builder`, `rustkmer-extract-{i}` precedent) — persistent workers and any new extractor threads; rayon is forbidden in blocking worker loops by the engine's own documented contract, and extractors block on bounded sends (same hazard)
- `std::sync::mpsc::sync_channel` — `SyncSender` is already clonable multi-producer/single-consumer: exactly the extractor→worker fan-in shape, no new channel type; backpressure semantics validated in v2.0 Phases 7–9
- Existing `PartitionLayout` / `RoutingBuffers` / `for_each_window` (pure, reentrant — the natural parallel unit is the record) — reused verbatim; per-key counting is commutative, so the exactness contract survives interleaved batches with no new synchronization
- `--features profiling` + `EngineDiagnostics.producer_nanos` / worker `busy_nanos` — the measurement harness for the decision gate; extend with per-stage producer timers, default builds untouched
- `scripts/bench/bench.py` — regression + MEM guardrail (peak RSS < jellyfish at both k: 43.97 / 68.52 GiB references) re-verified for any landed change

**The one conditional stack change:** flate2 `zlib-rs` backend feature (replacing `zlib`) — pulls zlib-rs ^0.6.7 transitively (MSRV 1.75, license Zlib, already reachable from the locked flate2 1.1.8). Use only if inflate measures ≥ ~20% of producer wall. Reversible with a one-line diff.

**Rejected (with reasons that should survive into planning):** `crossbeam-channel` (no capability gap — std `SyncSender` already clones), rayon on the producer/extractor send path (starvation hazard; see Architecture note below on the dispatcher-only-send variant), `rapidgzip-core` (MSRV 1.87 hard-conflicts with the 1.82 gate; only path in is a user-ratified MSRV raise, and the measurement gate says that branch is unlikely to open), `lgz` (MSRV undeclared/unverifiable; platform-skewed), `paraseq` (ownership model conflicts; pulls niffler, which this repo already removed once), `gzp` (parallel decompression only for block-delimited Mgzip/BGZF — our benchmark inputs are verified single-member standard gzip), `libdeflater` (no streaming), external `pigz`/`pugz` (pigz does not parallelize standard-gzip decompression; pugz is a research artifact), async runtimes (CPU-bound counting is the anti-case for async).

### Expected Features (MERGE-BENCH requirement set)

**Must have (table stakes — a credible merge verdict cannot ship without these):**
- Input-equivalence rules across arms + provenance recording (the comparison's validity axiom)
- **Jellyfish per-part count artifacts** — two same-`-m/-s/-C` `.jf` inputs at full scale; the v2.0 `jf-t16` artifact counted both parts in one invocation and is **not** usable as merge input (hash-size equality is enforced and the single most likely harness-biting constraint). Budget ≈ two full count runs of setup
- **Three-way parity gate:** merged == independent recount == cross-tool, per-k-mer exact — plus the fast pre-gate (Total conservation with the **sum-of-counts** definition, Distinct ≥ max input Distinct, input Totals match committed Phase-10 values: 897,266,581 / 8,967,099,203 at k=21; 1,146,353,600 / 8,275,694,030 at k=31)
- **Parity BEFORE timing** (phase10 precedent, locked)
- Counterbalanced reps (≥3) with rotation schedule and honest per-rep `cache_state`
- Wall + `max(rss, phys_footprint)` per rep; harness-internal clocks banned
- Verdict as pure recorded-median comparison at stated threads, both outcomes valid; exit-code contract 0/1/2; invest/no-invest recorded as the milestone deliverable
- Mechanical report render (byte-identical re-render proof; no measurement literals in code)
- Version + provenance pinning; hash-size fairness discipline (default 10G covers; state occupancy)
- Dual-k coverage (k=21 AND k=31 — the dense-u64/u128 storage split makes a single-k merge verdict half a verdict)

**Should have (differentiators):**
- Full per-k-mer count validation of the merged output — a stronger claim than the reference literature typically makes; the single most credible differentiator
- Invest/no-invest verdict with predicted-win sizing and "what would need to be true to revisit"
- Entry-rate / byte-rate metrics (makes the inherent format asymmetry visible: `.jf` ≈ 10 B/entry vs `.rkdb` 20 B/entry at k=21 — jellyfish merge moves ~half the I/O bytes at equal entry counts, an inherent format property, not a defect)
- Predicted-vs-measured cost-model check (linear-in-entries, single-threaded — a cheap falsifiable prediction)
- CI degradation rung: extend the existing synthetic two-part merge arm, never fork a second results schema

**Defer / anti-features:**
- KMC3/kmc_tools comparator — **descoped by user decision**; cutoff-capped counters (`-cs` default 255) change SUM semantics. Ecosystem context in a related-work note only
- Per-arm rustkmer merge flag tuning during the bench — measure DEFAULTS first; a config sweep is post-verdict work only on INVEST
- Comparing merged outputs via stats/totals only; testing mixed-canonicality/mixed-k arms (both tools reject mixed-k; jellyfish silently accepts mixed canonicality — measuring that documents its bug); N-way scaling and r1/r2 variants (post-INVEST only)

### Architecture Approach

Both tracks attach to structures that already exist and are pinned by tests — no speculative redesigns. **Merge side:** zero Rust changes. `bench.py` already provides counterbalanced rounds (`round_schedule` rotates tools, generalizes to 6 arms), per-rep `cache_state`, medians + CV%, zero-count sanity, fingerprints, schema validation, disk floor guard, and the count-parity pre-gate; `phase10.py` is the staged full-scale-controller precedent (optional `phase11.py` clone for the merge session). New harness work is additive: `jellyfish_merge_cmd`, the `jellyfish-count-B` / `jellyfish-merge` arms, merge parity gates, a deep slice-scale dump-vs-dump gate (full scale: stats-level only, stated honestly), an explicit arm-ordering assertion, and renderer merge-verdict sections (the current `_arm_row` merge `n/a` special case stays load-bearing for old results files). **PEXT side:** the producer bundle (`count_file_inner`, engine.rs:803–871) does everything except increment and measured ~99.99% of parallel wall; batches carry partition tags and per-key adds commute, so *who* produces a batch doesn't affect final tables — only the file-boundary flush-token accounting is order-sensitive.

**One open design point the roadmapper should carry forward:** the two researchers propose different attach topologies, both zero-deps and both exactness-preserving. ARCHITECTURE.md's Design A: dispatcher-only rayon tasks that parse/encode and **return** per-partition buffers — rayon never blocks on worker queues (so the documented hazard doesn't fire), the 2N+1 thread-exactness gate and flush protocol pass unchanged, and skip accounting stays producer-side and exact. STACK.md's Patterns A/B: E OS-thread extractors that parse, extract, route, and send via cloned `SyncSender`s (Pattern A = producer-per-file, natural fit to the six independent input parts; Pattern B = record-chunk handoff) — but a multi-sender flush requires a design decision (recommended: producers only route; caller flushes after a producer-join epoch). Both agree: records are the unit of parallel work, the single `for_each_window` funnel must not be forked, in-flight memory must be bounded, and the choice is made with attribution data in hand during the conditional phase's planning — not now.

### Critical Pitfalls

1. **Canonicality silent mixing (Pitfall 1, HIGH — demonstrated on the pinned binary).** `jellyfish merge` exits 0 on canonical/non-canonical inputs of the same reads and produces a meaningless database whose totals still conserve. Avoid: pin canonicality in harness config (one `BenchmarkConfig` drives both command lines), re-verify every input at P1, and make per-key equality the gate so this class structurally cannot pass.
2. **Vacuous parity gate (Pitfall 2).** Conservation-only checks pass even under key-space corruption AND under rustkmer's saturating-add clipping (WR-02). Avoid: define the three-way gate in writing before round 0; name the `total_kmers` definition per check (header = record count vs stats = sum of counts — the IN-03 collision); stream entries for conservation sums.
3. **Comparator-shape asymmetries (Pitfall 3).** Native formats per tool, 16-threads-vs-1 (jellyfish merge has no `-t`; documented "not parallelized and relatively slow"), defaults-only flags. Avoid: record threads/flags/routes/sha256 per arm, add a like-for-like `rustkmer merge --num-threads 1` arm, and state "each tool merges its own representation of identical, parity-validated input data" — one sentence that prevents a review cycle.
4. **Producer mis-attribution (Pitfalls 9/10, the most expensive failure mode available to v2.1).** Sizing extraction parallelism when inflate — inherently serial on a single stream — was actually the wall. Avoid: the arms A–D attribution design on the SHIPPED engine at full scale (stock / pre-decompressed / stage sub-timers / null consumer) with a pure-read control; predicted-win model names both ceilings (parallelizable share × worker-side scaling); never cite Phase-5-era profiles as current.
5. **Slice-scale D3 gating (Pitfall 14) + stale-doc contamination (Pitfall 7).** The slice wall is now dominated by output sort/write (Phase 8: 9.31 s wall, sort 1.70 s), so slice numbers mis-size the gate in both directions (the v1.0 "+420% from a slice on a substitute dataset" is the paid precedent), and the stale `docs/benchmark-report.md` headline (+420%, dataset deleted) contaminates sizing and context. Avoid: full-scale attribution only for the gate decision; drift fix landed in Phase 1 before anything new is written; all sizing cites v2.0 measured walls by named source run.

Also load-bearing: unfingerprinted/missing inputs (Pitfall 8 — sha256 + Total revalidation before round 0); full-scale confounds at 10× byte scale (Pitfall 5 — disk pre-flight 150–400 GiB transient estimate, scaled cooldown, thermal recording, honest cache_state); backpressure/teardown contracts in P4 (Pitfall 11 — every thread in the join set, error-injection tests at every boundary, no `sample` single-shot gates); boundary semantics (Pitfall 12 — warning-batch contract decision, no byte-stream slicing below record granularity, `checked_add` on every new aggregate site).

## Implications for Roadmap

Based on combined research, the suggested phase structure (final numbering belongs to the roadmap):

### Phase 1: Merge Characterization & Harness Prep (+ hygiene pulled forward)
**Rationale:** Characterize before burning multi-hour counterbalanced reps; every downstream measurement consumes one extended harness, so harness bugs are found at synthetic scale, not mid-session. The stale-doc fix MUST land here — before any new verdict exists that could contradict it or cite it.
**Delivers:** Jellyfish per-part count stage defined (same `-m/-s/-C`); harness extension (jellyfish-count-B / jellyfish-merge arms, `jellyfish_merge_cmd`, merge parity gates, slice-scale dump-vs-dump deep gate, arm-ordering assertion, renderer verdict section + unit tests); parity-gate spec in writing (three-way, definitions named); input decision (reuse vs regenerate) + fingerprints + retention plan; disk pre-flight budget; intermediate-scale jellyfish merge characterization (wall/output-size scaling); **full-protocol slice-scale dress rehearsal green** (both tools, parity pipeline, RSS/thermal/cache capture); `docs/benchmark-report.md` superseded banner/regeneration; Nyquist 5–8 and SECURITY.md 9/10 hygiene woven in per milestone scope.
**Addresses:** All MERGE-BENCH table stakes that are harness-side (FEATURES.md).
**Avoids:** Pitfalls 1, 2, 3, 4, 5 (pre-flight), 7, 8.

### Phase 2: Full-Scale Merge Verdict
**Rationale:** The milestone's headline deliverable, and it must complete **before** any PEXT implementation lands — a new binary hash changes provenance and would force re-running the merge session.
**Delivers:** Counterbalanced full-scale runs at both k; three-way parity executed (independent recount leg included — ~2.5 min per k, cheap enough that skipping saves nothing); medians + CV%; recorded verdict (invest/no-invest) via exit-code contract; mechanical report with methodology block (threads, flags, route per rep, cache_state, thermal, the single-threaded-comparator asymmetry note, like-for-like 1-thread arm).
**Uses:** The extended harness from Phase 1; phase10-style staged controller (optional phase11.py).
**Avoids:** Pitfalls 5 (protocol), 6 (axes pre-registered: wall primary, disk recorded, RSS context — no memory-win claims over a streaming comparator).

### Phase 3: Producer Attribution Research (PEXT)
**Rationale:** Evidence before architecture (standing user directive). Independent of Phases 1–2 — can overlap their window; changes nothing, so Phase 2's measurements stay attributable to a stable binary.
**Delivers:** Stage attribution table (inflate / parse / extract / route-send) measured on the SHIPPED engine at **full scale**, both k, builds fingerprinted; plain-vs-gzip differential with pure-read control; predicted-win model naming both ceilings (parallelizable share × min(worker-side scaling, measured producer scaling)); D3-gate decision memo. Expected outcome per current evidence: inflate ≈13% (below the ~20% zlib-rs gate), extraction+parse ≈85%+ → zero-deps extraction parallelization is the lever.
**Uses:** Existing `--features profiling` diagnostics; no new instrumentation required for the headline numbers.
**Avoids:** Pitfalls 9, 10, 13, 14.

### Phase 4: Parallel Extraction — CONDITIONAL (D3 pattern)
**Rationale:** Executes only if Phase 3's verdict justifies the predicted win; reuses Phase 1's harness for scaling and parity gates.
**Delivers:** Parallel producer per the chosen topology (dispatcher-only rayon tasks vs OS-thread extractors — decided in this phase's planning with attribution data); all ten invariants from ARCHITECTURE.md §3.2 as success criteria (partition disjointness, byte-exact differentials, `.rkdb` sha256 identity across thread counts, thread-observability gate — extended honestly if the topology changes it, flush/token happens-before, t1 honesty, bounded in-flight memory, frozen 12-method `PyCounter` surface, no-unwrap/error contracts, clean teardown); MEM guardrail **re-measured** at full scale, not asserted.
**Avoids:** Pitfalls 11, 12 (backpressure/teardown; boundary semantics — records as unit, warning-batch contract decision surfaced, `checked_add` everywhere, chimeric-edge fixtures).

### Phase Ordering Rationale

- **Only two hard dependencies:** Phase 3 → Phase 4 (research gates implementation — the D3 pattern), and Phase 2 → Phase 4 (provenance stability: a merged binary invalidates full-scale merge numbers). Phases 1 and 3 are mutually independent; running 3 concurrently with 1–2 is safe and cheap.
- **Phase 1 first** is cheap insurance: PEXT implementation (if triggered) is the second consumer of the extended harness, and both tracks' gates share the parity/render machinery.
- **Hygiene is not a phase — it is two pulled-forward items plus weaving:** the stale-doc fix is sequenced *into Phase 1* because its value is exactly "before anything new is written"; Nyquist 5–8 and SECURITY.md 9/10 thread through P1/P2 per milestone scope.
- **Grouping by architecture:** everything harness-side (no Rust changes) is one phase; everything measurement-only is Phase 3; the only code-changing phase is conditional and last.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 4 (if triggered):** topology decision (rayon-task dispatcher vs OS-thread extractors), flush-token contract design, queue-depth sizing as a measured knob, warning-batch contract decision, error-injection test matrix. Plan this phase with research-phase depth only if the D3 gate opens.
- **Phase 1:** only one genuinely open question — jellyfish merge runtime/memory at 20–90 GiB remains extrapolated until the intermediate-scale characterization (in-phase work, designed and ready).

Phases with standard patterns (skip research-phase):
- **Phase 1 (harness):** the research here is unusually complete — jellyfish semantics pinned empirically + source, parity gate specified, integration points file:line-anchored, phase10 precedent in-repo. Standard planning suffices.
- **Phase 2:** execution of a pre-registered protocol; no unknowns beyond Phase 1's characterization output.
- **Phase 3:** the phase IS research, and its measurement design (arms A–D, controls, sizing model) is already specified; planning is protocol scheduling, not investigation.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack (PEXT) | MEDIUM-HIGH | Zero-deps recommendation rests only on HIGH-confidence local facts (lockfile, direct experiments, code anchors); web-sourced crate facts (zlib-rs versions/benchmarks) are LOW per the classify-confidence seam but non-load-bearing — verify at integration if the inflate gate opens |
| Features (MERGE-BENCH) | HIGH | jellyfish 2.3.1 behavior verified against the installed pinned binary AND official source; kmc_tools semantics MEDIUM (single-source claim), irrelevant while KMC3 is descoped |
| Architecture | HIGH | Every integration point read from the actual code this session with file:line anchors; no speculative redesigns |
| Pitfalls | MEDIUM-HIGH | Codebase + jellyfish findings HIGH (direct reading, pinned-binary experiments); macOS thermal/cache methodology MEDIUM (≥2 sources); gzip-parallelization claims MEDIUM (carried, cross-checked) |

**Overall confidence:** HIGH — the build order, gates, and verdict axes do not hinge on any LOW-confidence number.

### Gaps to Address

- **PEXT attach topology** (rayon-task dispatcher vs OS-thread extractors): two researchers, two valid designs, different thread-observability consequences (2N+1 unchanged vs 2N+M+1 gate change). Resolve in Phase 4 planning with Phase 3 attribution data; pin the choice with tests.
- **Jellyfish merge full-scale behavior:** runtime, output file size (capacity-derived), and disk/wall budgets at 20–90 GiB are extrapolated. Phase 1's intermediate-scale characterization closes this before Phase 2 schedules rounds.
- **Merge disk budget:** 150–400 GiB transient is an estimate. Re-derive from v2.0 measured DB sizes in Phase 1; expect to raise `--disk-floor-gb` (default 150 was sized for count artifacts).
- **Input artifact existence:** whether per-part `.rkdb`/`.jf` inputs survive on disk or must be regenerated is undecided. Phase 1 decides reuse-vs-regenerate; either way sha256 + Total revalidation before round 0.
- **zlib-rs facts** (version, MSRV, benchmark deltas): web-sourced, LOW confidence. If the inflate gate opens, verify with `cargo tree`/docs.rs and a build under MSRV 1.82 before adopting.
- **Warning-batch grouping contract** (legacy per-4096-record wording): contract or incidental — must be decided and differential-asserted in Phase 4 planning if it runs.
- **Dataset description drift:** the split directory now holds **six** single-member gzip parts (~2.79 GB each, ~16.7 GB total), while PROJECT.md's "two parts, ~5.2 GB" is stale. The pinned benchmark arrangement remains part_001 + part_006; fix the description as part of the Phase 1 hygiene sweep (it also means multi-file producer-per-file has six independent files to spread across if PEXT runs).
- **Nyquist 5–8 and SECURITY.md 9/10:** scoped in milestone requirements but not detailed in these research files; carry as Phase 1/2 checklist items, not research gaps.

## Sources

### Primary (HIGH confidence)
- Pinned-binary experiments, jellyfish 2.3.1 (Homebrew, this host, 2026-11-16) — merge/info/dump/count semantics, canonicality-mixing demonstration, 6.8 MB merge RSS, capacity-derived output size; digests in research-store
- gmarcais/Jellyfish official source — `merge_main.cc`, `merge_files.cc`, `mer_heap.hpp` (k-way min-heap, single-threaded, counter_len = min, input-0 params inherited)
- rustkmer codebase (2026-11-16 tree, file:line-anchored) — `src/count/engine.rs` (producer bundle, flush/token, Drop-join, diagnostics), `src/count/partition.rs`, `src/count/batch.rs`, `src/kmer/extract.rs`, `src/cli/commands/{count,merge}.rs`, `src/database/{format,streaming_merge,stats,query}.rs`, `pyo3/src/counter.rs`, `tests/thread_pool_size_tests.rs` (2N+1 gate)
- Harness in-repo — `scripts/bench/bench.py` (protocol, parity pre-gate, renderer), `phase10.py` (staged controller, exit-code contract), `output_stage.py` (rotation, cache purge), plus `.planning/PROJECT.md` (v2.0 verdicts: 144.69/194.85 s k=21; MEM guardrail 43.97/68.52 GiB; Phase 7 producer-bound and Phase 8 slice-wall records; D3 pattern)
- Local experiments — inflate throughput (~1.2–1.3 GB/s on a 256 MiB slice); six-part gzip member scan (all single-member)

### Secondary (MEDIUM confidence)
- Official docs — jellyfish(1) manpages (merge BUGS: not parallelized, "relatively slow"; no `-s` on merge; variable-length counters), KMC 3.x `kmc_tools` docs (counter modes, `-cs` cutoff)
- Cross-checked web — Apple Silicon page-cache (`sudo purge` limited reclaim) and thermal-order-bias studies (up to 54% sequential-order bias on fanless-class); pigz docs (decompression not parallelizable); rapidgzip arXiv 2308.08955 (speculative block discovery)
- Kerbiriou & Chikhi 2019 (HiCOMB) — pugz speculative gzip decompression

### Tertiary (LOW confidence — verify at integration if the branch opens)
- flate2 docs / Trifecta Tech Foundation blog / Cargo PR #15417 — zlib-rs "fastest backend overall" claims, inflate deltas, MSRV 1.75, flate2 1.1.7+ direct-dep path
- docs.rs crate pages — gzp 2.0.4, lgz 0.3.17 (MSRV undeclared), rapidgzip-core 0.3.1 (MSRV 1.87), libdeflater 1.26.x, paraseq 0.6.3

---
*Research completed: 2026-11-16*
*Ready for roadmap: yes*
