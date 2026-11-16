# Feature Research: Merge Benchmark Semantics (MERGE-BENCH)

**Domain:** k-mer database merge operations — `jellyfish merge` semantics, ecosystem merge tools, and what a fair rustkmer-vs-jellyfish merge benchmark requires
**Researched:** 2026-11-16
**Confidence:** HIGH (jellyfish 2.3.1 behavior verified against the installed pinned binary AND the official source; kmc_tools semantics MEDIUM — official docs, no second source for one claim)

**Scope note:** This file serves the v2.1 MERGE-BENCH requirement set only. The PEXT (producer-bound extraction) target is covered by the parallel SUMMARY/ARCHITECTURE research; its only coupling to this file is the shared verdict-reporting pattern (D3 conditional-phase discipline), noted in Differentiators.

---

## Part 1 — What `jellyfish merge` Actually Does (verified ground truth)

All findings in this section were verified two ways: (a) empirically, by running the locally installed **jellyfish 2.3.1** binary (the pinned v2.0 comparator, `/opt/homebrew/bin/jellyfish`) on controlled inputs, and (b) against the official source of the 2.x series (`sub_commands/merge_main.cc`, `jellyfish/merge_files.cc`, `include/jellyfish/mer_heap.hpp` at gmarcais/Jellyfish). This is not folklore.

### Exact CLI surface a harness author must match

```
Usage: jellyfish merge [options] input:string+
  -o, --output=string          Output file (default mer_counts_merged.jf)
  -m, --min                    Compute min count instead of sum (default false)
  -M, --max                    Compute max count instead of sum (default false)
  -j, --jaccard                Compute jaccard and weighted jaccard similarities (default false)
  -L, --lower-count=uint64     Don't output k-mer with count < lower-count
  -U, --upper-count=uint64     Don't output k-mer with count > upper-count
```

The canonical merge invocation for the benchmark: `jellyfish merge -o merged.jf p1.jf p2.jf` (default = SUM of counts).

Note the flag collision hazard: in `jellyfish count`, `-m` is mer length; in `merge`, `-m` is MIN mode. A harness that copies flag strings between the two subcommands will silently produce wrong semantics.

### Input constraints (all verified empirically; error strings from source)

Every input after the first is checked against the first file's header. **All** must match:

| Constraint | Error on mismatch | Harness implication |
|---|---|---|
| key_len (= 2k bits) | `Can't merge hashes of different key lengths (42, 38)` | same `-m` k for all jellyfish count arms |
| hash size (`-s`) | `Can't merge hash with different size (1048576, 16777216)` | same `-s` for every per-part jellyfish count |
| reprobing strategy (max_reprobe_offset) | `Can't merge hashes with different reprobing strategies` | same jellyfish version/config |
| hash function matrix | `Can't merge hash with different hash function` | same jellyfish build |
| format (binary/sorted vs text) | `Can't merge files with different formats (...)` | use `count` output directly (it is binary/sorted) |

**Same-k enforcement:** rustkmer has the mirror constraint (`validate_merge_compatibility` in `src/cli/commands/merge.rs`). Both tools fail closed — the benchmark never needs to define what a mixed-k merge would mean.

**Canonicality is NOT checked and the flag is LOST (empirically verified):** merging two `-C` (canonical) databases exits 0 and the output header has **no `canonical` key** (`jellyfish info` reports `canonical: no`). The stored k-mers are still canonicalized (that happened at count time), but any downstream consumer that keys off the header flag sees a non-canonical DB. Consequence for the harness: canonicalization equivalence between the rustkmer and jellyfish arms must be established at **count** time and validated at **dump/parity** time — it cannot be inherited from merge output headers.

**Hash-size equality is the constraint most likely to bite the harness:** the per-part jellyfish counts must use the identical `-s`. This means the MERGE-BENCH jellyfish arm needs its own per-part count artifacts (see Dependencies); the v2.0 `jf-t16` arm counted both parts in ONE invocation, so `phase10-jf-t16.jf` is **not** usable as a merge input.

### Algorithm and cost model (from source, merge_files.cc / mer_heap.hpp)

- **K-way min-heap merge** (`mer_heap::heap`) over N file iterators. Heap items compare by (file slot position `pos_`, then key) — the `.jf` binary/sorted files are arrays sorted by reprobed hash slot, so this is a classic sorted-run k-way merge, not a hash join.
- **Single-threaded.** There is no thread creation anywhere in `merge_files.cc`; the jellyfish 1.x manual even carried a BUGS note that merge "has not been parallelized and is relatively slow", and the 2.x docs state running `merge` "should never be necessary" because `count` auto-grows and merges intermediates itself. Merge is a maintenance subcommand for jellyfish, not a first-class workflow.
- **Streaming / O(1)-per-input memory.** One iterator + heap item per input file; memory does not scale with k-mer count or hash size. Buffers only.
- **Count algebra per distinct key:** SUM (default), MIN, MAX computed during the run of equal keys across inputs; `-L/-U` filter the merged value. Note: when a key is absent from some inputs, MIN counts it as 0 (i.e. MIN over present files is compared against 0 — absent ⇒ minc forced to 0).
- **Output:** a new `.jf` binary/sorted file written with **input file 0's** hash parameters (size, reprobes, matrix) and `counter_len = min(counter_len across inputs)`. No auto-grow of the output hash — the union must fit the inherited slot count. At benchmark scale with `-s 10G` inputs holding ~450M distinct each and a union ~800–900M distinct, occupancy roughly doubles but stays well within capacity; the harness should state this.
- **Counter width:** `counter_len` is in bytes (4 ⇒ u32 counts, same as rustkmer's u32). SUM overflow across many inputs is unchecked by jellyfish; rustkmer sums saturate (`saturating_add`, `src/database/format.rs:1722`). With 2 human-scale parts and u32 counters, overflow is not a realistic concern; document, don't engineer for it.
- **Quirk (verified by running it):** `-j/--jaccard` does not write a database — it writes `Jaccard <x>` / `wJaccard <y>` text INTO the `-o` FILE. Irrelevant for MERGE-BENCH (sum is the target semantic), but worth knowing so a mis-flagged run is recognized.

### Byte-size asymmetry worth stating in the report (estimated, LOW-MEDIUM confidence)

Jellyfish binary/sorted entry ≈ ceil(2k/8) + counter_len bytes (k=21: ~6+4 = 10 B/entry; measured 25-entry file: ~10.4 B/entry). rustkmer `.rkdb` is fixed 20 B/entry (16-byte u128 k-mer + 4-byte count). So at k=21 jellyfish merge moves roughly half the I/O bytes of a `.rkdb` merge at equal entry counts, independent of any tuning — an inherent format property, not a defect on either side. The cost model is: wall ≈ linear in total input entries + union output entries, single-threaded, small constant memory. **No published human-scale `jellyfish merge` timings exist** (searched; the jellyfish paper's human numbers are counting at 32 threads). MERGE-BENCH produces the first-party numbers; expected behavior above is an inference from verified source, to be tested, not assumed.

---

## Part 2 — Feature Landscape

### Table Stakes (a credible MERGE-BENCH must have these)

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Input equivalence across arms | The comparison is meaningless unless both tools merge databases built from the SAME two parts with identical k, canonicalization, and (for jellyfish) identical `-s` — merge hard-fails on size mismatch | LOW | Harness ordering rule; record the exact count commands in provenance (jellyfish headers already embed their cmdline) |
| Jellyfish per-part count artifacts | `jellyfish merge` needs two same-size `.jf` inputs; the existing v2.0 jf arm artifact cannot be reused (single invocation over both parts) | MEDIUM | New stage: count part_001 and part_006 separately with the same `-m/-s/-C`, at full scale (~2× count-arm cost in setup) |
| Three-way parity gate: merged == recount == cross-tool | SUM semantics are exactly additive, so `merge(p1,p2)` must equal `count(p1∪p2)` exactly for BOTH tools AND equal each other per k-mer. Tool-vs-tool agreement alone can hide a shared bug | MEDIUM | Full per-k-mer map equality via dumps (`jellyfish dump -c` vs rustkmer dump); canonicalization decided at count time (see canonical-flag finding). Phase 10 precedent: "parity before timing — counts are exact and nonzero before any median is trusted" |
| Parity BEFORE timing | A faster wrong merge is worthless; phase10 already locks this pattern | LOW | Reuse phase10 gate structure verbatim |
| Counterbalanced reps with rotation | Single-order runs confound tool with cache state | LOW | `output_stage.rotation_schedule(arm_names, reps)` exists — every round visits every arm with rotated start |
| Honest per-rep `cache_state` | v1.0 decision: record the true purge result, never assume cold | LOW | `attempt_cache_purge` exists; copy the schema contract |
| Memory as `max(rss, phys_footprint)` + wall from rusage | v2.0 memory-bar discipline; harness-internal clocks are banned by the README | LOW | bench.py/phase10 measurement plumbing reusable |
| Verdict as pure recorded-median comparison at stated threads, both outcomes valid | An honest NO is a valid measured outcome (v1.0 BENCH-02 precedent; invest/no-invest is the milestone's deliverable) | LOW | Exit-code contract 0/1/2 like phase10 |
| Mechanical report render from recorded JSONs | Byte-identical re-rendering proved no hand-typed numbers (phase10 precedent, 8/8 verified) | MEDIUM | Reuse render-stage pattern; new merge-specific template |
| Version + provenance pinning | jellyfish 2.3.1 recorded; rustkmer binary from a release build; dataset fingerprints in manifests | LOW | Existing provenance machinery |
| Hash-size fairness discipline | Undersizing jellyfish `-s` silently penalizes the reference (README already warns for count; merge output also reuses input `-s`, so the union must fit) | LOW | Default 10G covers; state occupancy in the report |

### Differentiators (how rustkmer's verdict reporting can stand out)

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Full per-k-mer count validation of the merged output | Most published k-mer tool evaluations compare stats lines or file sizes; exact map equality is a stronger claim than the reference literature typically makes | MEDIUM | Same comparator machinery as the parity gate; this is the single most credible differentiator |
| Invest/no-invest verdict as an explicit recorded outcome with a cost model | Extends the D3 pattern: the report carries predicted-win sizing and the decision, not just wall times; a NO ships with "what would need to be true to revisit" | LOW | Pure reporting; no Rust changes |
| Entry-rate / byte-rate metrics (entries/s, bytes/entry) | Enables cross-scale and cross-k extrapolation from one measured rung; also makes the 10-vs-20-byte format asymmetry visible instead of hidden inside wall times | LOW | Derived from counts + rusage wall; no new measurement |
| Predicted-vs-measured cost model check | The Part 1 cost model (linear in entries, single-thread) gives a cheap falsifiable prediction; the report can state whether the reference behaved as modeled | LOW | One derived column |
| Degradation ladder rung for merge in CI | Synthetic two-part merge keeps the gate green on machines without CRR1936095 (existing harness philosophy: degrade, never skip silently) | MEDIUM | bench.py synthetic mode already builds count-A/count-B DBs and a merge arm — extend, don't fork |
| Dual-k coverage (k=21 AND k=31) | v2.0 measured both k for counting; merge verdict at one k only would be half a verdict given the dense-u64/u128 storage split at k=32 | LOW | Same controller, two configs |

### Anti-Features (seem good, are problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Adding kmc_tools/KMC3 to the merge verdict | "More comparators = more credible" | Explicitly descoped (user decision 2026-11-16); KMC counters are cutoff-capped (`-cs`, default 255) so its SUM semantics differ from exact-u32 tools — a three-way comparison would need a semantics caveat that swamps the message | Mention kmc_tools semantics as ecosystem context in the report's related-work note only |
| Per-arm flag tuning of rustkmer merge (`--merge-mode`, `--use-prefix-cache`, `--batch-size`) during the bench | "Pick the best config to win" | Turns a measurement into an optimization session; v2.1 explicitly defers merge implementation investment until the verdict justifies it | Measure DEFAULTS first (one config, the bounded-path default); a flagged config sweep is post-verdict work only if the verdict says INVEST |
| Mixing warm- and cold-cache reps without recording state | More reps, faster | Every median becomes uninterpretable (v1.0 lesson: honest `cache_state: unavailable` was the accepted answer) | Keep per-rep purge attempts + honest labels exactly as output_stage does |
| Comparing merged outputs only via `stats`/totals | Cheap | Aggregate totals can coincide while per-k-mer counts diverge; misses the actual merge contract | Full per-k-mer map equality (the parity gate above) |
| Testing mixed-canonicality or mixed-k merge behavior as a benchmark arm | "Coverage" | Both tools reject mixed-k; jellyfish silently ACCEPTS mixed canonicality with garbage semantics — measuring that is documenting jellyfish's bug, not benchmarking rustkmer | One parity-gate assertion that all arms used identical canonicalization settings |

## Feature Dependencies

```
[Input-equivalence rules]
    └──requires──> [Jellyfish per-part count artifacts]   (same -m/-s/-C)
                       └──requires──> [Full-scale part provisioning]  (exists: bench.py slice / phase10 input resolution)

[Three-way parity gate]
    └──requires──> [Jellyfish per-part count artifacts]
    └──requires──> [Per-k-mer dump comparator]            (new comparator code)
    └──blocks──> [Counterbalanced timing reps]            (parity before timing)

[Counterbalanced timing reps]
    └──requires──> [rotation_schedule + cache purge]      (exists: output_stage.py)
    └──requires──> [Jellyfish merge arm]                  (new command builder)
    └──requires──> [rustkmer merge arm]                   (exists: build_merge_cmd)

[Verdict + mechanical report]
    └──requires──> [Recorded medians + cache_state + peak bytes]
    └──requires──> [Exit-code contract]                   (phase10 pattern)

[CI degradation rung]
    └──requires──> [Synthetic two-part merge arm]         (exists in bench.py; extend)
    └──conflicts──> [Full-scale-only protocol]            (ladder must not fork the schema)
```

### Dependency Notes

- **Parity gate blocks timing:** phase10 locks "parity before timing"; a merge controller that times before parity is invalid by project precedent.
- **Per-part jellyfish artifacts are the critical new dependency:** everything in the jellyfish arm hangs off producing two same-`-s` `.jf` files; budget the setup cost (≈ two full count runs) into the phase plan.
- **bench.py synthetic merge arm conflicts with a new schema:** extend the existing arm and validator (`validate_schema` in bench.py) rather than forking a second results format.

## MVP Definition

### Launch With (MERGE-BENCH minimum)

- [ ] Input-equivalence rules + provenance recording — the comparison's validity axiom
- [ ] Jellyfish per-part count stage (same `-m/-s/-C`, full scale) — enables the reference arm
- [ ] Jellyfish merge arm + rustkmer merge arm at defaults — the two measured arms
- [ ] Three-way parity gate (merged == recount == cross-tool, per-k-mer exact, nonzero) — correctness before speed
- [ ] Counterbalanced reps (≥3, phase10 precedent) with honest `cache_state` — fair timing
- [ ] Wall + `max(rss, phys_footprint)` per rep — both guardrail metrics
- [ ] Verdict from recorded t-median comparison at both k, exit-code contract, invest/no-invest decision recorded — the milestone deliverable
- [ ] Mechanical report render — byte-identical re-render proof

### Add After Validation (v1.x)

- [ ] Entry-rate / byte-rate derived metrics — once raw medians are trusted
- [ ] Predicted-vs-measured cost-model column — cheap, strengthens the verdict narrative
- [ ] Synthetic/slice degradation rungs in CI — after the full-scale protocol is frozen

### Future Consideration (v2+)

- [ ] N-way (>2 input) merge scaling — only if the verdict justifies merge investment
- [ ] r1/r2 arrangement variants beyond the pinned two-part split — dependent on INVEST
- [ ] Config sweep (`--merge-mode` × `--use-prefix-cache`) — post-verdict, only on INVEST

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Jellyfish per-part count artifacts | HIGH | MEDIUM | P1 |
| Three-way parity gate | HIGH | MEDIUM | P1 |
| Counterbalanced reps + cache_state | HIGH | LOW | P1 |
| Merge arms (both tools, defaults) | HIGH | LOW-MEDIUM | P1 |
| Verdict + mechanical report | HIGH | MEDIUM | P1 |
| Entry/byte-rate metrics | MEDIUM | LOW | P2 |
| Cost-model check column | MEDIUM | LOW | P2 |
| CI degradation rung | MEDIUM | MEDIUM | P2 |
| Config sweep / N-way | LOW (until INVEST) | HIGH | P3 |

## Competitor Feature Analysis

| Feature | jellyfish merge 2.3.1 (pinned reference) | kmc_tools (KMC 3.x, ecosystem context only) | rustkmer merge (subject) |
|---|---|---|---|
| Constraint checks | Same k, hash size, reprobe, matrix, format — all enforced; canonicality NOT checked, flag dropped | Same k enforced in practice; counter cutoff (`-cs` 255 default) shapes semantics | `validate_merge_compatibility`; k/canonical from `.rkdb` headers |
| Count algebra | SUM (default), MIN, MAX via `-m/-M`; `-L/-U` filters | intersect default **min**, union default **sum**; modes min/max/sum/diff/left/right; complex expression language (`*` intersect, `+` union, `-` kmers_subtract, `~` counters_subtract) | SUM only (saturating u32); no min/max/jaccard modes |
| Algorithm | Single-threaded k-way min-heap over sorted-file iterators | Disk-backed sorted-database operations (KMC 3 multi-threaded `kmc_tools`) | Bounded-memory: in-memory / streaming / prefix-cache routes, rayon parallelism, admission control |
| Memory model | O(1) per input, streaming | Disk-oriented, RAM-light | Admission-controlled vs `--max-memory`; chunk-bounded streaming |
| Output | `.jf` sorted hash, inherits input-0 params, counter_len = min(inputs), no auto-grow | KMC db | `.rkdb` v2, sorted by k-mer value, 20 B/entry |
| Status in own docs | "should never be necessary" (count auto-merges) | First-class feature set | First-class v1.0 feature (bounded-memory was the milestone goal) |

The benchmark-semantic assumptions of the two reference points differ materially: jellyfish merge assumes exact u32 counts and identical hash geometry; kmc_tools assumes cutoff-capped counters and set-operation algebra. rustkmer's merge benchmark is therefore cleanest against jellyfish — same exact-count semantics — which matches the project's pinned-comparator decision.

## Sources

- jellyfish 2.3.1 installed binary (`/opt/homebrew/bin/jellyfish`) — merge/info/dump/count behavior verified live, 2026-11-16 (HIGH)
- gmarcais/Jellyfish official source (main branch): `sub_commands/merge_main.cc`, `jellyfish/merge_files.cc`, `jellyfish/merge_files.hpp`, `include/jellyfish/mer_heap.hpp` (fetched via GitHub API) (HIGH)
- KMC 3.x official docs, `doc/kmc_tools/{simple,complex}.tex` at refresh-bio/KMC — counter modes and defaults (HIGH); same-k enforcement not quoted from manual (MEDIUM, single-source)
- Jellyfish user guide / 1.x man pages — merge "should never be necessary"; 1.x BUGS: not parallelized, slow (web sources: cbcb.umd.edu jellyfish manual; Debian manpages) (MEDIUM)
- rustkmer local source: `src/cli/commands/merge.rs` (`validate_merge_compatibility`, rayon pool), `src/database/format.rs:1722` (saturating_add), `src/database/streaming_merge.rs` (HIGH)
- rustkmer harness: `scripts/bench/README.md`, `bench.py` (`build_merge_cmd`, `DEFAULT_HASH_SIZE = "10G"`, `validate_schema`), `phase10.py` (arms, parity-before-timing, median verdict, mechanical render), `output_stage.py` (`rotation_schedule`, `attempt_cache_purge`) (HIGH)
- KMC tool docs: [kmc_tools usage.tex](https://github.com/refresh-bio/KMC/blob/master/doc/kmc_tools/usage.tex), [Debian kmc_tools-complex manpage](https://manpages.debian.org/buster/kmc/kmc_tools-complex.1)
- Jellyfish docs: [jellyfish manual (UMD)](https://www.cbcb.umd.edu/software/jellyfish/jellyfish-manual.html), [jellyfish(1) manpages](https://manpages.debian.org/jessie/jellyfish/jellyfish.1#1)

---
*Feature research for: rustkmer v2.1 MERGE-BENCH (merge benchmark semantics and fair-comparison requirements)*
*Researched: 2026-11-16*
