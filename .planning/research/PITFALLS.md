# Pitfalls Research

**Domain:** Adding (a) a full-scale rustkmer merge vs `jellyfish merge` benchmark and (b) a producer-bound / parallel-extraction research track to an EXISTING shipped exact-count k-mer system (rustkmer v2.1 "Merge Verdict & Producer Research")
**Researched:** 2026-11-16
**Confidence:** MEDIUM-HIGH — codebase findings are HIGH (direct code reading, file:line anchors); jellyfish merge semantics are HIGH (official manpage + experiments run on the pinned 2.3.1 binary installed on this host); macOS thermal/cache methodology claims are MEDIUM (cross-checked, ≥2 sources); gzip-parallelization claims are MEDIUM (carried from the 2026-11-11 v2.0 research cache, cross-checked there).

This document covers only the two v2.1 investigation targets. The v2.0 pitfalls research (2026-11-11, below in git history) remains valid for minimizer/disk-backed/hasher work — that track is descoped this milestone. Here the system already ships and the exact-count contract, golden baselines, and parity gates are *paid for*: the risks are measurement verdicts corrupted by semantic mismatch, confounds, and stale evidence.

---

## How to Read This Document

**Phase labels** (working names for the roadmapper; final numbering belongs to the roadmap):

| Label | Working name | Scope |
|-------|--------------|-------|
| **P1** | Merge Characterization & Harness Prep | Pin `jellyfish merge` semantics, define the parity gate (what equals what), extend the harness, fingerprint merge inputs, full-protocol dry run at slice scale |
| **P2** | Full-Scale Merge Verdict | Counterbalanced full-scale runs, gates, measured verdict → invest/no-invest, renderer-generated report |
| **P3** | Producer Attribution Research | Decompress-vs-extract split measured on the SHIPPED engine, predicted-win sizing at full scale, D3-gate decision for P4 |
| **P4** | Parallel Extraction (conditional) | Executes only if the P3 verdict justifies it (v2.0 D3 pattern) |
| **HYG** | Hygiene (cross-cutting) | `docs/benchmark-report.md` drift fix, Nyquist validation, SECURITY.md — woven through P1/P2 |

P1 precedes P2 (characterize before burning multi-hour counterbalanced reps); P3 precedes P4 (evidence before architecture — the standing user directive). Every "phase to address" below assumes that ordering.

**Empirical basis established during this research** (pinned `jellyfish 2.3.1`, Homebrew, this host; stored in `research-store`):

| Fact | Evidence | Consequence |
|------|----------|-------------|
| `merge` has NO `-s` output-hash-size option (manpage `-s` is input-buffer size; installed help shows no `-s` at all) | manpage + `jellyfish merge --help` | The pre-registered worry "merge's `-s` distorting RSS" is moot; sizing is internal |
| Merge operation defaults to additive SUM (`-m` min / `-M` max / `-j` jaccard are opt-in alternatives) | `--help` + measured: Total 48M = 24M + 24M | Same additive semantics as rustkmer merge — parity is meaningful |
| k-mer length mismatch is refused loudly: `Can't merge hashes of different key lengths (6, 10)`, exit 1 | tiny-fixture experiment | Good fail-loud; no guard needed |
| **Canonical vs non-canonical mismatch is NOT refused**: merging a non-canonical hash with a canonical hash of the same reads exits 0 and produces 12 distinct keys where the canonical truth is 7 — while Total stays conserved (32 = 16 + 16) | tiny-fixture experiment | Pitfall 1: conservation checks cannot catch key-space mixing; only per-key parity can |
| Merge peak RSS is tiny and scale-weak: 6.8 MB merging two 240 MB `.jf` files (2M-entry hashes), vs 212 MB for count of the same data | `/usr/bin/time -l` on this host | Pitfall 6: merge is a streaming k-way merge — memory-superiority framing is vacuous here |
| Merge output `.jf` file size is capacity-derived (240,000,834 B ≈ input's 240,000,890 B), not content-derived | `ls` on outputs | Disk planning must budget by hash capacity, not distinct keys |
| `jellyfish dump` default is FASTA-like (count in header); `-c` gives 2-column `kmer<TAB>count`; `-L/-U` filter counts | `--help` + manpage | Parity pipeline uses `-c`, sorts both sides identically |
| jellyfish counts use variable-length encoding ("there is no maximum value in the hash", `-c` default 7 bits, `--out-counter-len` default 4 B) | manpage | Exact counts on both sides at our scale; overflow semantics differ but cannot fire at k=21/31 human coverage |

---

## Critical Pitfalls

### Category A — Merge benchmark: semantics & correctness

### Pitfall 1: Canonicality mismatch silently merges different key spaces — and every aggregate check still passes

**What goes wrong:**
The merge-bench arms get fed databases whose canonical flags disagree (one tool counted canonical, the other didn't; or one part-database was produced by a different code path). `rustkmer merge` refuses (its `validate_merge_compatibility` checks k AND canonical mode), but **`jellyfish merge` exits 0** and emits a plausible file: forward-strand keys and canonical keys coexist as distinct keys, counts split across them. Demonstrated on the pinned binary: non-canonical (11 distinct) + canonical (7 distinct) of the *same reads* → merged "12 distinct, Total 32" with `ACG 4` — a semantically meaningless database. If the parity gate compares only `jellyfish stats` totals against rustkmer stats, both sides agree (totals are conserved!) and the verdict ships on garbage.

**Why it happens:**
Canonicality is baked into the database at count time, not at merge time. jellyfish merge treats whatever keys are stored as opaque bit patterns and validates only key *length*. rustkmer's own guard cannot warn about the *comparator's* inputs. The failure is invisible in every aggregate.

**How to avoid:**
- Pin canonicality in the harness config, not in discipline: one `BenchmarkConfig` drives BOTH command lines (the v1.0 `bench.py:172-173` pattern) and asserts `canonical=True` for every input it produces or consumes.
- Re-verify each input's canonical mode at P1: `rustkmer stats <db>.rkdb` reports canonical mode; for `.jf` inputs, dump a sample and check that revcomp keys are absent (`GGT` must appear as `ACC`-style canonical forms when -C was on), or simpler: regenerate `.jf` inputs from the same count runs that the parity gate already validated rather than resurrecting unverified files.
- Make per-key equality the gate (Pitfall 2), so this class of failure structurally cannot pass.

**Warning signs:**
`jellyfish stats` Distinct on merged output ≈ sum of input Distincts (near-zero key overlap) when the inputs demonstrably share most keys; dump shows both a k-mer and its reverse complement as separate keys; per-key diff reports missing/complementary keys in complementary pairs.

**Phase to address:** P1 (harness config + input verification). Confidence: HIGH (empirically demonstrated on the pinned binary).

---

### Pitfall 2: "What equals what" left undefined until after the runs — conservation invariants become the whole gate

**What goes wrong:**
The team runs 3 counterbalanced reps per arm (hours each), then discovers nobody specified the correctness contract for a *merged* output. The cheap checks that exist (merged Total == sum of input Totals; merged Distinct within union bounds — the v1.0 slice-run checks, `docs/benchmark-report.md:51-52`) all pass, and the report calls it "parity". But Total conservation holds even under Pitfall 1's key-space corruption, and rustkmer's saturating-add merge summation (`streaming_merge.rs:509`, triaged debt WR-02) would also conserve totals while clipping. The verdict rests on checks that structurally cannot fail.

**Why it happens:**
Merge correctness is a three-way question and only its easiest leg is cheap: (a) rustkmer-merge vs **independent recomputation** — a single count over the union of the reads that produced the inputs (the merge of disjoint-part databases must equal one count over all parts — this is the only check anchored outside the two tools); (b) rustkmer-merge vs jellyfish-merge **per key**; (c) aggregate conservation. (a) costs ~2.5 min per k at v2.0 measured rates (147 s count wall) — cheap enough that skipping it saves nothing.

**How to avoid:**
- Define the gate in P1, in writing, before any full-scale rep:
  1. **Pre-gate (fast):** conservation — merged Total == Σ input Totals; merged Distinct ≥ max input Distinct; every input Total itself matches the committed Phase-10 parity values (897,266,581 / 8,967,099,203 at k=21; 1,146,353,600 / 8,275,694,030 at k=31).
  2. **Ground truth (once per k):** independent recomputation — count the full read set with rustkmer and diff against the merged database, per key, byte-exact. If inputs are NOT a clean partition of one read set, this leg is redesigned, not skipped silently.
  3. **Cross-tool parity (the verdict gate):** dump both merged outputs, normalize to `(canonical k-mer string, count)` pairs, sort identically, diff — equality must be exact.
- State which `total_kmers` definition every check uses: `DatabaseHeader::total_kmers` is the **record count** (`entries.len()`, `format.rs:659,737`) while `KmerCounter::total_kmers` and `rustkmer stats` report the **sum of counts** (`stats.rs:196`) — the IN-03 collision. A conservation check that mixes them fails mysteriously or passes vacuously. Recompute sums by streaming entries; never trust the header field for conservation.
- Overflow note: rustkmer merge uses `saturating_add` (WR-02) while jellyfish's variable-length counters don't cap. At k=21/31 human coverage (max count ~10⁴–10⁵) neither can fire — record that in the report as a stated scope condition, and keep the u32::MAX boundary tests from v1.0 covering the merge path.

**Warning signs:**
The gate spec is written after the first full-scale run; "parity" sections cite only Distinct/Total equality; a per-key diff is deferred as "phase 2 work"; someone compares `header.total_kmers` against `stats.total_kmers` and gets a 897-million-vs-9-billion mismatch that "must be a harness bug".

**Phase to address:** P1 (define), P2 (execute). Confidence: HIGH (code-anchored + v1.0 precedent).

---

### Pitfall 3: Comparator-shape asymmetries — each tool merges its own representation, at different thread counts, possibly with different merge semantics

**What goes wrong:**
Three asymmetries hide inside "rustkmer merge vs jellyfish merge":
1. **Input representation:** rustkmer reads `.rkdb`; jellyfish reads `.jf`. The inputs are different files encoding the same k-mer counts. That is the honest design (each tool consumes its native format), but if unstated, readers assume identical inputs and either distrust the verdict or "fix" it by converting formats — which measures a different workload (dump → re-ingest).
2. **Parallelism:** jellyfish merge is single-threaded (manpage BUGS: "has not been parallelized and is relatively slow"; no `-t` option exists; measured 10.8G cycles vs count's 53.8G on the same fixture host). rustkmer merge defaults to all cores via rayon. A raw wall comparison is 16-threads-vs-1; a verdict that doesn't say so overstates the gap, and a reviewer who discovers it dismisses the whole report.
3. **Merge operation:** `-m`/`-M`/`-j` produce entirely different outputs (min/max/jaccard). Running defaults gives SUM — fine — but nothing records that choice, and a later re-run with a stray flag compares apples to min.

**Why it happens:**
Each asymmetry is individually defensible ("that's how the tool works"); together they make the comparison underspecified. The v1.0 report survived this only because its methodology section recorded thread counts, `-s 10G`, and the decompression arrangement explicitly.

**How to avoid:**
- Record in the harness config and print in the report: input files + sha256 per side, thread counts per arm (`--num-threads` pinned, not defaulted), and the full comparator flag set (`merge -o out.jf in1.jf in2.jf` — defaults only, stated).
- Add a **secondary like-for-like arm**: `rustkmer merge --num-threads 1` at least once per k, so the report contains a single-thread-vs-single-thread row alongside the "what a user gets" row. (rustkmer's `--num-threads` is accepted and mapped; parallel merge work is rayon-based — record what 1 thread actually changes in the route.)
- State in the report that "each tool merges its own representation of identical, parity-validated input data" — one sentence, prevents a review cycle.

**Warning signs:**
The report has no thread-count line for merge arms; someone proposes piping a dump through the other tool "to make inputs identical"; two reps of the same arm disagree wildly and the diff discussion never mentions parallelism.

**Phase to address:** P1 (harness), P2 (report). Confidence: HIGH (manpage + binary help + measured cycles).

---

### Pitfall 4: Discovering a jellyfish merge limitation AFTER burning full-scale reps

**What goes wrong:**
The first thing learned about `jellyfish merge` at full scale is learned mid-protocol: e.g. it turns out to take hours on 20 GiB inputs (single-threaded, "relatively slow"), or its `.jf`-capacity-derived output files (measured: output file size ≈ input capacity, 240 MB for a hash whose content is a fraction of that) blow the disk budget between reps, or the Phase-10 `.jf` outputs were deleted and regenerating them re-runs count. Any mid-protocol surprise invalidates counterbalancing (arms must interleave in rounds) and costs hours per rep.

**Why it happens:**
Everything so far (v1.0 slice-scale merge, v2.0 count verdicts) characterized jellyfish *count*, not *merge*. The research for this document pinned the semantics on small fixtures, but runtime/memory at 20–90 GiB remains extrapolated until a scaled dry run executes.

**How to avoid:**
- P1 ends with a **full-protocol dress rehearsal at slice scale**: same harness code path, same parity pipeline (dump → normalize → sort → diff), same RSS/thermal/cache capture, jellyfish merge included. Exit criteria: every gate green, every artifact fingerprinted, protocol timings recorded.
- Characterize remaining unknowns at an intermediate scale first (e.g. 2–4 GiB `.jf` inputs): wall time scaling, output file size, stderr/exit codes. Extrapolate to full scale and sanity-check disk/wall budgets against them before scheduling the counterbalanced rounds.
- Decide input shape in P1 and stick to it: which databases (2 part-databases per k from the split parts), produced fresh or reused from Phase 10 (see Pitfall 8), same shape both tools.

**Warning signs:**
The first full-scale round is also the first time `jellyfish merge` runs at >1 GiB scale; the harness grows a "retry with different flags" branch during P2; counterbalancing degrades to "rustkmer first because it's faster to get results".

**Phase to address:** P1. Confidence: HIGH on the mechanism (v1.0's parity-gate halt on attempt 1 is the exact precedent, `docs/benchmark-report.md:109-111`).

---

### Pitfall 5: Full-scale confounds — disk exhaustion, thermal history, page-cache warmth, and write-back

**What goes wrong:**
At 40–90 GiB scale the merge benchmark measures the machine as much as the tools:
- **Disk:** per full-scale rep, each tool writes an output of the same order as its inputs (rustkmer `.rkdb` ≈ 20 B/entry → ~18 GiB at k=21, ~21 GiB at k=31 per input; jellyfish `.jf` capacity-derived, likely tens of GiB each), plus prefix-cache merge temp chunks on the same or another volume. Three reps × two tools × two k ≈ 150–400 GiB transient (estimate) — ENOSPC mid-rep kills the round and, worse, a near-full APFS volume silently changes write performance.
- **Thermal history:** fanless-class Apple Silicon shows up to ~54% sequential-order bias in sustained sweeps; back-to-back long I/O+memory-bandwidth reps heat-soak the machine, and the counterbalancing (round-robin) exists precisely for this — but only if rounds actually interleave and cooldown is real. The v2.0 protocol's 5 s cooldown was tuned for 2.5-min count runs; 40–90 GiB merge reps need a longer, pre-registered cooldown, and `pmset -g therm` state should be recorded per rep (readable without sudo).
- **Page cache:** merge reads 20+ GiB inputs sequentially — rep 1 cold, rep 3 warm can differ on the order of 2× on an I/O-dominated arm. `sudo purge` on Apple Silicon reclaims only ~50–800 MB and cannot evict active pages, so cold-cache cannot be *guaranteed* on this host — exactly why the v1.0/v2.0 honesty discipline (record true `cache_state` per rep; declare cold-cache "PARTIALLY satisfied") exists and must carry into P2 verbatim.
- **Write-back:** neither tool fsyncs; rep N's dirty output pages flush during rep N+1's window. A too-short cooldown imports the previous rep's flush cost into the next measurement.

**Why it happens:**
Count-arm confound controls were sized for count-arm costs; merge arms are 10× the bytes moved. "It worked at slice scale" is the trap — at slice scale all of these effects are noise-level.

**How to avoid:**
- Pre-flight disk budget in the harness (the v1.0 harness already has a disk guardrail to copy): refuse to start unless free space ≥ budget for all planned outputs + temps; clean per-rep outputs (or write to a scratch volume) with the temp-lifecycle discipline.
- Keep counterbalanced rounds truly interleaved; pre-register a cooldown scaled to rep duration (e.g. cooldown ≥ 10–20% of rep wall, or until `pmset -g therm` thermal pressure drops); record thermal state per rep in the results JSON.
- Record `cache_state` per rep per arm exactly as v2.0 did; state the cold-cache caveat honestly in the report rather than claiming purged caches.
- One warmup per tool, discarded, as in v2.0 — this also stabilizes allocator/page-cache state.

**Warning signs:**
CV wall on a merge arm >10% (the v1.0 k=31 jellyfish count arm hit 14.8% — flagged); free-space drops by hundreds of GiB during the run; later rounds systematically faster than earlier rounds within the same arm; `pmset -g therm` shows sustained thermal pressure during rounds 2–3.

**Phase to address:** P2 (protocol), P1 (disk pre-flight + dry run). Confidence: MEDIUM-HIGH (thermal/cache claims cross-checked web; disk figures are arithmetic on committed entry counts).

---

### Pitfall 6: Porting the count-arm memory framing to merge — jellyfish merge is a streaming tool, so "leaner than jellyfish" is vacuous in this comparison

**What goes wrong:**
The milestone's standing guardrail is "peak RSS below jellyfish" — true and meaningful for count (43.97 vs 46.84 GiB k=21; 68.52 vs 88.00 GiB k=31). Carrying that framing into the merge comparison predicts a false win: measured on the pinned binary, jellyfish merge of two 240 MB hashes peaked at **6.8 MB RSS** (streaming heap-based k-way merge) — it will hold ~tens of MB at full scale too. rustkmer merge streams at 32 B/k-mer *charge* but its chunk buffers and prefix-cache machinery will measure orders of magnitude above jellyfish merge's RSS. Two wrong conclusions are available: "rustkmer merge is 1000× worse on memory" (true, meaningless — both are trivially small) or "our merge needs memory work to beat jellyfish" (misdirected investment).

**Why it happens:**
The guardrail was written for the count comparison where jellyfish's `-s`-sized hash dominates RSS. Merge has no `-s`, no in-memory rebuild — the RSS floor disappears. The pre-registered measurement discipline (max(rss, phys_footprint)) is still right; the *framing* of what the number means is what breaks.

**How to avoid:**
- Pre-register in P1 what the merge verdict's decision axes are: wall time (primary), disk cost (outputs + temp, recorded), peak RSS (recorded honestly with max(rss, phys_footprint) — but reported as context, not as a win/loss axis).
- Record which rustkmer merge route each rep took (streaming vs prefix-cache vs in-memory — the admission control routes by `--max-memory` and input size, `format.rs:989-1015`): a route change between reps silently compares different algorithms. Benchmark the default route ("what a user gets") and state the chosen route in the results JSON.
- Keep the MEM guardrail where it belongs: any *performance change* to counting/extraction (P4) keeps full-scale count peak RSS below jellyfish. Merge benchmarking adds no such constraint.

**Warning signs:**
A draft report table shows "RSS vs jellyfish: +4000%" as a loss; someone proposes raising `--max-memory` "to win the memory column"; results JSON lacks a route field for rustkmer merge arms.

**Phase to address:** P1 (pre-registration), P2 (report). Confidence: HIGH (measured 6.8 MB on pinned binary; admission constants code-anchored).

---

### Pitfall 7: Stale-doc contamination — old verdicts leak into the new one (and the new verdict lands next to a contradicting headline)

**What goes wrong:**
`docs/benchmark-report.md` still leads with the v1.0 k=21 **+420%** verdict — measured on a substitute dataset (CRR2044018, since deleted from disk) with the pre-engine binary. The authoritative v2.0 verdict (k=21 CLI 144.69 s vs 194.85 s — rustkmer *faster*) lives in planning artifacts. Three concrete contamination paths: (a) the merge report or its summaries quote v1.0 numbers as current context ("rustkmer is 5× slower at k=21, so merge is probably bad too"); (b) the PEXT research sizes the producer win against the stale 505 s k=21 wall instead of 144.69 s — inflating the predicted win ~3.5×; (c) HYG's drift fix happens *after* P2 ships, so the repo's visible benchmark doc and the fresh merge verdict contradict each other on the same page set.

**Why it happens:**
The stale file is mechanically rendered and internally consistent — it looks authoritative. The v1.0 report even says its input "no longer present on disk (verified 2026-11-14)", which is easy to miss. LLM- or human-summarized context tends to cite the most readable doc.

**How to avoid:**
- Fix the drift FIRST (HYG item pulled into P1, not deferred): add a superseded banner or re-render `docs/benchmark-report.md` with a provenance line ("v1.0 snapshot; superseded by v2.0 Phase-10 verdicts; dataset deleted") so no later artifact can cite it unqualified.
- The merge verdict report is generated by the same mechanical renderer discipline (`bench.py --render-report`; renderer contains no measurement literals; re-render reproduces byte-for-byte) from committed result JSONs — no hand-written numbers.
- Every PEXT sizing computation cites v2.0 measured walls (144.69 / 147.08 s CLI) as its baseline, and the citation names the source run, not "the benchmark report".

**Warning signs:**
Any sentence in new planning docs containing "+420%", "505 s", "CRR2044018", or "5× slower at k=21" without the word "superseded"; the merge report's context section citing a report whose input fingerprint says "no longer present on disk".

**Phase to address:** HYG pulled into P1 (before P2 writes anything); P3 for sizing baselines. Confidence: HIGH (file contents verified 2026-11-16).

---

### Pitfall 8: Unfingerprinted or missing merge inputs — the verdict rests on unreproducible data

**What goes wrong:**
The merge arms need input databases: 2 rustkmer `.rkdb` (one per split part, per k) and 2 jellyfish `.jf`. If they are regenerated ad hoc without fingerprints, or reused from Phase 10 without revalidation (and possibly deleted since — the v1.0 report's own inputs vanished this way), then the parity gate validates nothing, and a mid-run regeneration silently changes the workload mid-counterbalancing.

**Why it happens:**
v2.0's count arms counted the complete r1 set per run; per-part databases may never have been persisted as artifacts. Reusing count *outputs* feels free until provenance questions start.

**How to avoid:**
- P1 decides: reuse vs regenerate. Either way, every input artifact gets size + sha256 recorded in the results JSON (the harness already fingerprints inputs — keep it), plus a revalidation pass: the pre-gate of Pitfall 2 (input Totals match the committed Phase-10 parity values) runs before round 0.
- Keep inputs on disk for the whole milestone and note their retention in the report (the anti-v1.0-lesson: committed fingerprints make numbers re-runnable via `--input` even after deletion).
- If regenerating `.jf` inputs: they come from the same count runs whose parity rustkmer already proved — do not accept "close enough" `.jf` files from an unrecorded run.

**Warning signs:**
Results JSON lists inputs without sha256; a merge arm's input Total differs from the committed 897,266,581 / 8,967,099,203 (k=21) or 1,146,353,600 / 8,275,694,030 (k=31) values; someone deletes 40 GiB of inputs "to free space" between rounds.

**Phase to address:** P1. Confidence: HIGH (v1.0 measured precedent; parity values from PROJECT.md v2.0 record).

---

### Category B — Producer research & parallel extraction (PEXT)

### Pitfall 9: Decompression vs extraction mis-attribution — sizing the win on the wrong half of the producer

**What goes wrong:**
The producer bundle is: open → gzip inflate → bio record parse → `for_each_window` encode → partition-route → batch send (`count_file_inner`, `src/count/engine.rs:803-871`). Phase 7 established the count phase is producer-bound (single producer ≈99.99% of parallel wall), but "producer" is exactly the bundle PEXT wants to split. If attribution is wrong, the D3 gate is fed a phantom predicted win: e.g. extraction parallelism is built (P4 executes) when gzip inflate — which is *inherently serial* on a single stream — was 60% of the producer wall and got no faster. The phase spends its budget and moves the full-scale wall by the residual fraction. This is the single most expensive failure mode available to v2.1.

Two specific mis-reads to guard against:
- **Kernel-wait is not extraction:** the Phase 5 profile showed 57.86% kernel wait/spin/syscall self-time — on-CPU self-time tables that don't subtract wait make any stage look hot. That profile is also from the *old DashMap engine* — citing its 38% "DashMap increment/hash" number against the current partitioned engine is stale evidence of the same kind as Pitfall 7.
- **Byte-volume asymmetry:** the gz-vs-plain comparison (T_gz − T_plain ≈ inflate share) has a confound — the plain run reads ~3.1× the bytes from disk (~16 GiB vs ~5.2 GB for CRR1936095 r1). On this host's NVMe that's likely seconds, not tens of seconds, but it must be measured (pure-read control), not assumed.

**How to avoid (the concrete measurement design, all on the SHIPPED engine, builds fingerprinted with sha256 + commit):**
1. **Arm A — stock:** gz input at a fixed random-record slice; record wall + `producer_nanos` (profiling feature; exists at `engine.rs:195-204`).
2. **Arm B — pre-decompressed:** the same records pre-inflated to plain `.fq` at rest; `producer_nanos(A) − producer_nanos(B)` ≈ inflate share, corrected by a pure-read control that reads both files with no parsing (calibrates the byte-volume effect).
3. **Arm C — stage sub-timers:** extend the profiling feature with per-stage producer timers (inflate / parse / extract / route-send), default builds untouched. This decomposes the producer without behavior change; the existing `producer_nanos` plumbing is the template.
4. **Arm D — null consumer:** parse + `for_each_window` encode, discard keys (no routing, no tables). B vs D isolates encode; D vs A isolates table/route cost.
- Deliverable: a written attribution table (fraction of producer wall per stage, with evidence per cell) that the D3 gate cites. If inflate dominates, the honest PEXT levers are file-level parallelism across the 2 split parts and producer/consumer overlap — not "parallel extraction" of a serial stream.
- Re-run attribution on the current engine even where Phase 5 numbers exist — the engine changed twice since (Phases 7–8).

**Warning signs:**
The P3 report has one number labeled "producer" with no stage split; the gz-vs-plain delta is reported without a pure-read control; any attribution citing the 2026-11-11 Phase 5 breakdowns as current; predicted win computed as "(extraction share) × threads" where extraction share actually includes inflate.

**Phase to address:** P3 (primary deliverable), P4 (only builds what the table justifies). Confidence: HIGH on the design; the code anchors (`engine.rs:803-871`, profiling feature) are HIGH.

---

### Pitfall 10: Over-threading / wrong lever — parallelizing extraction when the gz stream is the ceiling

**What goes wrong:**
"Parallel extraction" is interpreted as many extractors reading one gz stream. A single gzip stream inflates serially on one core (~150–400 MB/s/core; pigz's man page is explicit that decompression cannot be parallelized without specially prepared streams). N extractors then either (a) all block on one inflate (zero win, N−1 idle), or (b) someone splits the compressed stream at deflate-block boundaries — which requires speculative block discovery plus 32 KiB window reconstruction (rapidgzip-class, arXiv 2308.08955), a new dependency with real correctness surface (false-positive block finds must be trial-decoded), an MSRV audit, and gzip-block boundaries that do NOT align with FASTQ record boundaries. Meanwhile the safe lever — file-level parallelism across the two split parts (`part_001`, `part_006`) — is nearly free of these hazards but is left unexplored because "we already read both files in one loop".

**Why it happens:**
Thread-count is the visible knob. The Amdahl structure is invisible: predicted win = parallelizable-fraction × scaling-efficiency, and scaling-efficiency is capped by the *worker* side too — if extraction gets fast, workers' increment loops (memory-bandwidth-bound) become the new joint bottleneck, and extrapolating the producer win linearly overpromises.

**How to avoid:**
- P3's sizing model names the ceiling explicitly: predicted full-scale win ≤ (producer parallelizable share from Pitfall 9's table) × min(worker-side scaling ceiling, measured producer scaling). No P4 gate without this model.
- Order the levers: (1) file-level parallelism (2 producers, one per split part, each with its own partition tables merged via the exact checked `merge_local_counts` path — `engine.rs:494-517` precedent); (2) producer/consumer overlap refinement; (3) member-level parallel inflate for concatenated gzip; (4) rapidgzip-class only with a dependency audit (MSRV ≤ 1.82, no global allocator, multi-member regression 8102985 green, parity gate on real reads).
- RSS guard: every added producer/buffer multiplies partition-table memory at full scale — the MEM guardrail (peak RSS < jellyfish at both k) must be re-measured, not asserted, since v2.0's Phase 6 already saw per-worker partitioned RSS rise once before (25 GiB) and had to be re-engineered (down to ~18 GiB).

**Warning signs:**
A PEXT prototype shows great extraction-stage speedup but <10% full-scale wall movement; `top` shows threads mostly in `inflate` waiting; a dependency proposal mentions zstd/rapidgzip without an MSRV note; projected RSS at 16 producers × partition tables exceeds the jellyfish ceiling on paper before any run.

**Phase to address:** P3 (sizing model), P4 (lever order + guardrail re-measure). Confidence: HIGH on mechanism; MEDIUM on inflate throughput figures (cross-checked ecosystem data).

---

### Pitfall 11: Backpressure deadlocks and unclean teardown in the layered pipeline

**What goes wrong:**
The engine's parallel path is a contract: per-worker bounded `sync_channel(8)` batch queues + per-worker ack channels + token-checked flush barriers + Drop-joins-every-worker (`engine.rs:1125-1130`). Adding producer-side parallelism layers another bounded queue in front (or behind) and creates the classic failure set: (a) a worker error must unblock **every** blocked sender — today the worker drops its receiver and the producer's next send fails loud; with an intermediate stage, the error can strand a stage holding a full queue and the process hangs instead of failing; (b) `Drop` joins workers but a new producer thread that isn't in the join set leaks or hangs process exit (the `engine_drop_joins_workers` watchdog test exists precisely for this class); (c) queue depths tuned for the old producer rate misbehave at the new one — too deep inflates RSS (in-flight batches), too shallow serializes the pipeline the change was meant to parallelize. Separately, the known-flaky macOS `sample`-based thread-count test gets reused as a P4 acceptance gate and flakes under the new thread topology's races, burning verification cycles on phantom failures.

**Why it happens:**
Bounded backpressure is load-bearing correctness machinery, not an implementation detail — its invariants (senders drop on error; every thread in a join set; ack-before-flush-return) are easy to break while adding "just one more thread". The engine's own module docs enumerate these contracts (`engine.rs:44-53`); a parallel producer must extend them, not bypass them.

**How to avoid:**
- Design the new stage against the written contract: one owner per queue; any error drops all senders in its layer and propagates; the engine's join set covers every thread it spawned (Drop must return — keep the watchdog test shape and extend it to the new topology).
- Error-injection tests at every boundary: worker dies mid-stream (exists: `worker_overflow_returns_verbatim_error_without_hanging` — keep green); NEW: producer-side stage dies mid-stream; upstream reader errors mid-file; flush barrier racing a failing send. Every failure path must join everything and return the first error.
- Queue depth is a measured knob (sweep via the harness), never a guess; record chosen depths in the results JSON alongside RSS.
- Replace the flaky `sample`-based thread-count gate with deterministic assertions: `engine.worker_count()` (public API) plus named-thread enumeration (`rustkmer-count-{i}`) in tests; if `sample` is used at all, tolerate races (retry/threshold), never single-shot gate.

**Warning signs:**
A hang in CI that never reproduces locally; RSS growth proportional to queue depth changes; a PR that adds `std::thread::spawn` without adding the thread to a Drop-join path; verification flake reports on the `sample` test that get "fixed" by re-running.

**Phase to address:** P4 (design + tests). Confidence: HIGH (contracts code-anchored; flake fact from milestone context).

---

### Pitfall 12: Ordering and boundary semantics — order-independent counting hides order-dependent contracts

**What goes wrong:**
Counting itself is commutative (sum per key; 1-vs-N differentials prove it), which invites "records can go anywhere". But three artifacts are order- or boundary-dependent:
1. **Skip-warning batches:** the CLI prints one `Warning: Skipped {} k-mer{} with invalid characters in chunk` per 4096-record batch containing skips (`count.rs:255-260`; engine `SkipWarningBatch`, `engine.rs:1405-1444`) — legacy wording, batch grouping, and per-batch skip counts are all observable. Parallel record distribution regroups the 4096-record batches; a differential on warning *output text* breaks even when counts are byte-identical.
2. **Rolling-encoder record boundaries:** any parallel batching that slices the byte *stream* (not records) can split a record across extractors; a rolling 2-bit encoder state carried across the boundary emits chimeric k-mers spanning records — the exact bug class v2.0 paid for on the Python surface (D2: 33 chimeric k-mers eliminated). Multi-line FASTQ records also break fixed-byte-offset splitting.
3. **`skipped_windows` totals:** parallel producers make every aggregate a new summation site — the engine's convention is `checked_add` with verbatim overflow messages (`engine.rs:83-90`); a parallel-extraction path that sums with `+=` silently weakens it.

**Why it happens:**
The extractor is funneled through ONE `for_each_window` (`engine.rs:1008,1025`) — a parallel producer that keeps that funnel inherits the semantics; the risk is a "faster" path that forks a second extractor or slices raw bytes for throughput.

**How to avoid:**
- Records are the unit of parallel work. No byte-stream slicing below record granularity; no lookahead across record boundaries; the rolling encoder (if introduced) resets per record and is differential-tested against `encode_kmer_bytes_u128` on the edge matrix before adoption (v2.0 pitfall 10 carried forward, now scoped to PEXT paths).
- Decide in P4's plan whether warning-batch grouping is contract or incidental: if contract, the parallel path must regroup warnings in sequential record order (or the decision to change output text is surfaced like every user-visible change — WR-04/D2 precedent). Whatever is decided, a differential asserts it.
- All new summation sites use `checked_add` + verbatim messages; the message text is contract-pinned by tests.
- Extend the 2N+1 gate (byte-identical `.rkdb` across thread counts, reachable RED control) to the new topologies — new thread counts, new producer counts, same fixture matrix.

**Warning signs:**
Warning lines change count or wording under a thread-count change; distinct counts rise slightly on N-containing reads only (chimeric emission fingerprint); a 1-vs-2-producer differential fails only on multi-line-FASTQ fixtures; totals differ between producer topologies by amounts proportional to skip counts.

**Phase to address:** P4 (design), P4 verification (differentials). Confidence: HIGH (all anchors in code; chimeric precedent from v2.0 Phase 9).

---

### Pitfall 13: Page-cache warmth mis-attributed to extraction wins in the PEXT microbenches

**What goes wrong:**
Arm B of the attribution design (Pitfall 9) requires pre-decompressing ~16 GiB to plain `.fq` — which *warms the page cache for exactly the file the plain arm then reads*. A/B arms run sequentially and B wins partly on cache. The same applies to any repeat-rep microbench: second-and-later reps read from cache, first reps don't; interleaving matters. A "1.5× producer win" that is really "1.5× on warm cache" inflates the D3 gate the same way Pitfall 9's mis-attribution would, just from the I/O side. (Merge-bench arms have the identical issue at 20+ GiB scale — Pitfall 5 — but PEXT microbenches are where it interacts with attribution.)

**Why it happens:**
Pre-decompression is unavoidable for Arm B; the confound is in the design, not a mistake. v2.0 already learned the general lesson ("honest `cache_state: unavailable` x30"; counterbalanced reps), and the +6.6%-shrinks-to-3.5% back-to-back measurement effect is the canonical warning.

**How to avoid:**
- Counterbalance arm order at the rep level (A,B,B,A / B,A,A,B) and record `cache_state` per rep per arm, exactly as the v2.0 protocol did.
- The pure-read control (Pitfall 9, step 2's correction) doubles as the cache-sensitivity probe: run it cold-ish first and warm; if its delta is material, report attribution bounds rather than a point estimate.
- Slices fit in RAM more easily than full inputs — say so in the report: slice-scale cache effects are *larger*, another reason the D3 gate sizes at full scale (Pitfall 14).

**Warning signs:**
Arm B beats Arm A in every rep regardless of order; the pure-read control's time is nonzero and unreported; attribution deltas shrink when the schedule is counterbalanced after being designed sequentially.

**Phase to address:** P3 (protocol). Confidence: MEDIUM-HIGH (protocol precedent in-repo; cache claims cross-checked web).

---

### Pitfall 14: Sizing the D3 gate from slice scale — the slice wall is dominated by output sort/write, not the producer

**What goes wrong:**
Phase 8's measured finding: after the output-stage work, **"the slice wall is now dominated by output sort/write"** (PROJECT.md Phase 7/8 record: real 4M slice t16 23.83 → 9.31 s, sort delta 8.91 → 1.70 s). At slice scale, a producer improvement therefore moves the wall only a little — and a naive P3 measurement at slice scale *understates* the producer share, while a naive prototype *celebration* at slice scale overstates nothing at all because the wall doesn't move. Either way, slice-scale numbers mis-size the predicted full-scale win, and the D3 gate (execute P4 only if the win is worth it) fires wrong in both directions. The v1.0 k=21 "+420% from a slice on a substitute dataset" is the paid precedent for slice-scale verdicts.

**Why it happens:**
Full-scale runs cost ~2.5 min each — cheap by P2 standards but 100× a slice run, so the temptation is to extrapolate. The composition of the wall (producer vs sort/write vs output) changes with scale because distinct-k-mer volume and output size grow superlinearly relative to records.

**How to avoid:**
- P3 sizes the predicted win at full scale: at least one attribution pass (Pitfall 9 arms A/C) on the full CRR1936095 r1 set per k. At ~2.5 min per count run this is minutes of machine time for the decision that gates an entire conditional phase.
- If slice runs are used for development iteration, calibrate the sort/write share at full scale and *subtract it* before quoting producer shares — state the correction in the report.
- The predicted-win model (Pitfall 10) consumes full-scale producer shares only.

**Warning signs:**
The P3 report's producer-share table cites only 4M-record slices; the D3 gate decision text references "at slice scale"; a prototype's full-scale A/B is deferred "until P4".

**Phase to address:** P3. Confidence: HIGH (Phase 8 measured record; v1.0 precedent).

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Parity via `jellyfish stats` totals only (skip per-key diff) | Minutes saved on gate design | Structurally cannot catch key-space mixing (Pitfall 1); verdict untrustworthy | **Never** as the whole gate; fine as the fast pre-gate |
| Quoting stale reports (v1.0 k=21 +420%) as context | Saves a look-up | Contaminates verdicts and sizing (Pitfall 7); contradicts shipped results | **Never** unqualified; only with a "superseded, substitute dataset" label |
| Comparing merge walls without recording thread counts/routes | Simpler config | Report unverifiable; route changes between reps silently compare algorithms (Pitfalls 3, 6) | **Never**; record both, add the 1-thread arm |
| Reusing intermediate databases without sha256 + Total revalidation | Hours saved on regeneration | Parity gate validates nothing; unreproducible verdict (Pitfall 8) | Only with fingerprints + pre-gate revalidation |
| Skipping the full-protocol slice dry run | One day saved in P1 | Mid-protocol surprises invalidate counterbalancing (Pitfall 4) | **Never** before first full-scale round |
| Slice-scale extrapolation for the D3 gate | Fast iteration | Wall composition differs at scale; verdict mis-sized both directions (Pitfall 14) | Dev iteration only; never for the gate decision |
| `+=` on new aggregate sites in parallel paths | Saves typing | Wraps silently; violates the checked-sum convention (`engine.rs:83-119`) | **Never** |
| Forking a second extractor in a parallel reader | Feels faster | Chimeric k-mers at boundaries; semantics drift (Pitfall 12) | **Never**; extend the single `for_each_window` funnel |
| Trusting `sample`-based thread counts as gates | Easy to write | Known flake under races burns verification cycles (Pitfall 11) | Only with retry/tolerance; prefer `worker_count()` asserts |
| Deep queues "to be safe" | No stalls in dev | RSS inflation at full scale; MEM guardrail risk (Pitfall 11) | Measured knob, recorded in results |

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| `jellyfish merge` | Assuming count-arm knowledge transfers (e.g. `-s` sizing; expecting parallel speed) | Merge has no `-s`, is single-threaded, additive; characterize on the pinned binary (done in this research; re-verify at P1) |
| `jellyfish dump` → parity pipeline | Parsing FASTA-style headers; unsorted diff | Use `dump -c` (2-column), `LC_ALL=C sort` both sides, `cmp` the streams; keys are unique so no stability concern |
| rustkmer `stats` vs `.rkdb` header | Mixing the two `total_kmers` definitions (sum-of-counts vs record count, IN-03) | Name the definition per check; stream entries for conservation sums |
| Merge admission routing | Benchmarking "rustkmer merge" without recording which route (streaming / prefix-cache / in-memory) ran | Record route per rep in results JSON (`format.rs:989-1015`); benchmark the default route, state it |
| Harness (`scripts/bench/`) | Adding merge arms outside the `BenchmarkConfig` single-source pattern | Extend `BenchmarkConfig`; both command lines derive from it (v1.0 `bench.py:172-173` pattern) |
| Results reporting | Hand-editing the verdict report | Renderer-generated from committed JSONs (`--render-report` discipline); hand-edits are detectable by re-render |
| Input lifecycle | Deleting multi-GiB artifacts mid-milestone to free space | Retention plan in P1; fingerprints make post-deletion re-runs possible via `--input` |
| Thermal state | Trusting the 5 s v2.0 cooldown for 40–90 GiB reps | Pre-register scaled cooldown; record `pmset -g therm` per rep |
| macOS page cache | Believing `sudo purge` gives cold caches on Apple Silicon | It reclaims ~50–800 MB of inactive pages only; keep honest `cache_state` recording |
| PyO3 surface (if P4 runs) | Measuring Python parity with a stale `.so` | Rebuild `pyrustkmer` (`maturin develop --release`, `.venv313`, unset CONDA_PREFIX) and assert module version in the session header |

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Serial inflate inside the producer | gz wall ≈ plain wall + inflate; extraction wins invisible in gz runs | Attribute first (Pitfall 9); file-level parallelism before stream splitting | Any gz input ≥ ~20% of producer wall |
| Kernel-wait read as stage cost | "Extraction is 57% hot" from self-time tables | Subtract wait; use profiling-feature stage timers on-CPU only | Every profile on I/O-coupled paths |
| Warm-cache A/B | Later arm wins consistently | Counterbalance + `cache_state` per rep | Every repeated-input benchmark |
| Write-back bleed | Rep N+1 slower than rep N within an arm | Cooldown scaled to rep size; warmup discarded | Reps ≥ tens of GiB written |
| Worker-side becomes joint bottleneck | Producer 2× faster, wall moves 10% | Model the joint ceiling (Pitfall 10); full-scale A/B before the gate | After any producer speedup lands |
| Disk near-full during rounds | Wall variance grows; ENOSPC kills round 3 | Pre-flight disk budget + per-rep cleanup | 150–400 GiB transient (estimate) |
| Slice-scale D3 gating | Prototype wins at 4M records, not at 5.2 GB gz | Full-scale attribution before the gate | Always (wall composition is scale-dependent) |

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Unvalidated parsing of the parity dump pipeline (sorting/normalizing tool output) | Malformed tool output crashes the harness mid-round; partial results mistaken for verdicts | Treat tool outputs as untrusted data; fail loud with exit codes; keep harness parsing separate from measurement |
| Temp/scratch sprawl in `scripts/bench/scratch/` | Hundreds of GiB of stale slice/temp outputs accumulate on the dev host | Reuse the temp-lifecycle discipline (TTL sweep pattern, `temp_lifecycle.rs`); scratch cleanup step in the harness |
| Running long counterbalanced rounds with sudo-purge workarounds from random blogs | Unvetted system modifications on the dev host | Only the documented no-sudo protocol (`cache_state` honesty); no new system-level hacks |

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Merge verdict report doesn't state thread counts, routes, or "each tool merges its own representation" | Readers can't judge what was compared; review cycles re-litigate methodology | One methodology block per the v1.0 report shape — it already carries these lines for count |
| PEXT research report jargon ("producer-bound", "D3 gate") without the 2-line plain statement | Stakeholders can't act on the invest/no-invest recommendation | Every report opens with the decision, the number, and the condition |
| Slow `jellyfish merge` surprises users of the *repo docs* | "rustkmer merge is slow" FUD from misread benchmarks | The report states comparator parallelism explicitly (single-threaded comparator; like-for-like 1-thread row present) |

## "Looks Done But Isn't" Checklist

- [ ] **Parity gate:** per-key three-way equality implemented (rustkmer-merge vs jellyfish-merge vs independent recount) — not just stats totals; pre-gate conservation used the *sum-of-counts* definition explicitly
- [ ] **Canonicality:** both sides' inputs verified canonical at P1; harness config asserts it; jellyfish silent-mix behavior documented in the report
- [ ] **Dry run:** full protocol (both tools, parity pipeline, RSS/thermal/cache capture) executed green at slice scale BEFORE round 0
- [ ] **Provenance:** every input and output artifact has size + sha256 in the results JSON; input Totals match committed Phase-10 values before round 0; retention plan stated
- [ ] **Methodology:** thread counts, comparator flags, merge route per rep, cooldown, `pmset -g therm`, `cache_state` per rep per arm — all recorded; like-for-like 1-thread arm present
- [ ] **Report:** generated by the renderer from committed JSONs; no measurement literals in code; supersedes-drift handled (`docs/benchmark-report.md` banner/regeneration landed BEFORE P2)
- [ ] **Verdict axes:** wall (primary) + disk (recorded) + RSS (context, max(rss, phys_footprint)) — no memory-win claims over streaming jellyfish merge
- [ ] **PEXT attribution:** stage table (inflate/parse/extract/route) measured on the SHIPPED engine, full scale, builds fingerprinted; pure-read control included; Phase-5-era profiles not cited as current
- [ ] **PEXT sizing:** predicted-win model names both ceilings (parallelizable share × worker-side scaling); D3 gate decision cites full-scale numbers only
- [ ] **P4 (if executed):** records-as-unit confirmed; warning-batch contract decision surfaced and differential-asserted; checked sums on new aggregates; 2N+1 differential extended to new topologies with reachable RED control; Drop-join watchdog extended; error-injection tests at every new boundary; `sample` flake not load-bearing; MEM guardrail re-measured at full scale
- [ ] **PyO3 (if P4 touches Python surface):** `.so` rebuilt and version-asserted before pytest; dual-surface benchmark shows the win on both

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Canonicality mixing discovered post-run (1) | MEDIUM | Discard the affected rounds (aggregates untrustworthy); fix input verification; re-run counterbalanced rounds from scratch — partial data must not be merged with post-fix data |
| Gate found vacuous after runs (2) | MEDIUM | Runs are reusable IF raw outputs + inputs are retained: implement the missing per-key/recount legs against retained artifacts; no re-measurement needed unless outputs were deleted |
| Comparator asymmetry raised in review (3) | LOW | Add the 1-thread arm + methodology lines; re-render report; no re-runs if arms were already recorded |
| Mid-protocol jellyfish limitation (4) | HIGH | Halt; characterize at intermediate scale; re-plan the counterbalanced schedule from round 0 (partial rounds are not counterbalanced) |
| ENOSPC / thermal / cache confound suspected (5) | MEDIUM | Check `cache_state`/thermal columns for systematic arm-order effects; if present, re-run affected rounds with fixed budget/cooldown; if absent, disclose and proceed |
| Memory framing error in draft report (6) | LOW | Move RSS to context column; re-state axes; re-render |
| Stale citation found in shipped verdict (7) | LOW-MEDIUM | Correct the citation, re-render; if sizing used stale baselines, redo the sizing math and re-run the D3 gate decision (not the measurements) |
| Input provenance gap (8) | MEDIUM | Regenerate + fingerprint inputs; revalidate pre-gate; re-run affected arms (counterbalancing forces round-level redo) |
| Wrong-half optimization built (9/10) | HIGH | The honest attribution table is written first; if P4 already executed on a phantom win, stop, re-baseline the model, and surface the sunk cost in the verdict — do not "finish" the phase to justify it |
| Deadlock / leak in P4 prototype (11) | LOW-MEDIUM | Extend watchdog + error-injection tests; fix tear-down contract; no verification credit until all injection paths pass |
| Boundary semantics regression (12) | MEDIUM | Differential matrix pinpoints the topology that breaks; fix within the single-extractor funnel; re-run 2N+1 matrix before merge to main |
| Cache-warm "win" (13) | LOW | Counterbalanced re-run of the affected arms; report attribution bounds |

## Pitfall-to-Phase Mapping

| # | Pitfall | Prevention Phase | Verification |
|---|---------|------------------|--------------|
| 1 | Canonicality silent mixing | P1 | Harness asserts canonical on all inputs; per-key gate passes on fixtures where the known-bad case is a reachable RED control |
| 2 | Undefined "what equals what" | P1 define, P2 execute | Three-way gate spec in writing before round 0; independent-recount leg green at both k |
| 3 | Comparator-shape asymmetry | P1 harness, P2 report | Methodology block lists threads/flags/representation; 1-thread arm present |
| 4 | Late jellyfish characterization | P1 | Full-protocol slice dry run green, including jellyfish merge arm and parity pipeline |
| 5 | Full-scale confounds | P1 pre-flight, P2 protocol | Disk pre-flight refusal works; `cache_state`/thermal columns populated; CV per arm < 10% or cv_warning flagged |
| 6 | Memory framing on merge | P1 pre-registration, P2 report | Verdict axes pre-registered; route recorded per rep; no RSS win/loss claims vs streaming comparator |
| 7 | Stale-doc contamination | HYG pulled into P1; P3 sizing | Drift fix landed before P2; grep of new artifacts shows no unqualified v1.0 numbers |
| 8 | Input provenance | P1 | sha256 + Total revalidation green before round 0; retention plan in report |
| 9 | Decompress-vs-extract attribution | P3 | Stage table on shipped engine at full scale; pure-read control reported; no Phase-5 citations as current |
| 10 | Over-threading / wrong lever | P3 model, P4 order | Predicted-win model with both ceilings; lever order documented; MEM guardrail re-measured if P4 executes |
| 11 | Backpressure / teardown | P4 | Watchdog drop test extended; error-injection matrix green at every boundary; no `sample` single-shot gates |
| 12 | Ordering / boundary semantics | P4 + verification | Warning-batch differential (contract decision recorded); 2N+1 byte-identity matrix extended; chimeric edge fixtures green |
| 13 | Cache-warm microbenches | P3 | Counterbalanced schedule in protocol; attribution reported as bounds where cache sensitivity is material |
| 14 | Slice-scale gating | P3 | D3 gate decision text cites full-scale numbers; sort/write share calibrated or subtracted |

## Sources

**Codebase (HIGH — direct reading, 2026-11-16):**
- `src/count/engine.rs` (producer bundle `count_file_inner` :803-871; flush/ack/backpressure contracts :44-53, :1255-1299; Drop-join :1125-1130; checked-sum convention :83-119; `merge_into` exact path :494-517; skip-warning batches :1405-1444; profiling `producer_nanos` :195-204)
- `src/cli/commands/count.rs` (verbatim warning wording :255-260; thread precedence chain)
- `src/database/format.rs` (admission constants 96/32 B/k-mer :81-97; routing :989-1015; header `total_kmers` = record count :659, :737; saturating-add sites)
- `src/database/streaming_merge.rs:509` (merge `saturating_add` — WR-02 triaged debt), `src/database/stats.rs:196` (stats total = sum of counts)
- `src/cli/commands/merge.rs` (compatibility validation; `--num-threads`/route flags)
- `docs/benchmark-report.md` (v1.0 verdict +420%; substitute dataset; deleted-input note :96-98; parity-gate halt precedent :109-111; methodology shape)
- `scripts/bench/` (harness, `BenchmarkConfig` pattern, counterbalanced protocol, baselines), `.planning/research/profiling/` (Phase 5 breakdowns — marked STALE for current-engine claims)
- `.planning/PROJECT.md` (v2.0 measured verdicts; Phase 7 producer-bound record; Phase 8 slice-wall-composition record; D3 pattern; MEM guardrail numbers)

**Pinned-binary experiments (HIGH — jellyfish 2.3.1, Homebrew, this host, 2026-11-16; digests stored via `research-store`):**
- `jellyfish merge --help` / `jellyfish dump --help` (no `-s`; additive default; `-c/-t/-L/-U`)
- K-mismatch refusal + canonical-mismatch silence + conservation-despite-mixing (tiny fixtures)
- Merge RSS 6.8 MB vs count 212 MB on 240 MB inputs; output file capacity-derived

**Official docs (HIGH):**
- [jellyfish(1) man page (Ubuntu resolute, 2.3.x)](https://manpages.ubuntu.com/manpages/resolute/man1/jellyfish.1.html) — merge BUGS section ("not parallelized... relatively slow"; hash does not grow in memory), dump format, variable-length counters ("no maximum value in the hash")
- [Debian jellyfish 2.3.0 UserGuide source](https://sources.debian.org/src/jellyfish/2.3.0-15/doc/UserGuide.lyx/) — hash sizing rules, merge guidance
- [Jellyfish GitHub](https://github.com/gmarcais/Jellyfish) — upstream (raw fetch blocked from this host; semantics pinned via manpage + local binary instead)

**Web (MEDIUM — cross-checked, ≥2 sources; digests stored):**
- [Does sudo purge actually work on Apple Silicon?](https://www.theodorehq.com/shiny/blog/does-sudo-purge-work-apple-silicon) and [sudo purge how-to](https://www.theodorehq.com/shiny/blog/sudo-purge-apple-silicon-howto) — limited reclaim (~50–800 MB), inactive-pages only
- [Fanless Mac thermal-throttling benchmark study (round-robin + median mitigation)](http://uvp.y42u.net/blog/uwview-pro-thermal-throttling-benchmark/) — up to 54% sequential-order bias
- [USENIX Security '23 M1 study](https://www.usenix.org/system/files/usenixsecurity23-taneja.pdf) — fan-cooled frequency-constrained vs passively-cooled thermally-constrained
- [macOS purge how-to (macperformanceguide)](https://macperformanceguide.com/CommandLine-howto-purge-disk-cache.html) — purge semantics, "approximate initial boot conditions"
- [Apple-silicon-bench FAQ](https://github.com/carlosacchi/apple-silicon-bench/wiki/FAQ#1) — variance norms
- Carried from the 2026-11-11 v2.0 research cache (cross-checked there): pigz man page (decompression not parallelizable); rapidgzip arXiv 2308.08955 (speculative block discovery, window reconstruction)

**Research cache:** 6 digests stored via `research-store` (keys from `research-plan`), 2026-11-16.

---
*Pitfalls research for: rustkmer v2.1 Merge Verdict & Producer Research (merge benchmark semantics/confounds + parallel-extraction attribution)*
*Researched: 2026-11-16*
