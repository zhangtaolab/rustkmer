# Pitfalls Research

**Domain:** Adding minimizer-partitioned / disk-backed / faster-hasher counting to an EXISTING exact-count k-mer system (rustkmer v2.0 "k=21 Counting Parity")
**Researched:** 2026-11-11
**Confidence:** MEDIUM-HIGH — codebase findings are HIGH (direct code reading, file:line anchors below); external algorithm/ecosystem claims are MEDIUM (cross-checked, ≥2 sources); a few single-source doc claims are flagged LOW.

This document replaces the v1.0 pitfalls research (2025-06-30). The v1.0 pitfalls were largely *paid for and fixed* — this round is about not re-paying them while adding KMC-class architecture to a system that already has exact-count contracts, golden baselines, and two public surfaces.

---

## How to Read This Document

**Phase labels** (working names for the roadmapper; final numbering belongs to the roadmap):

| Label | Working name | Scope |
|-------|--------------|-------|
| **P1** | Root-Cause Profiling & Foundations | Evidence before architecture (user directive 2026-11-11): decompression-vs-counting split, hashing-cost validation, binary fingerprinting, CLI/Python extraction-semantics decision, shared-core groundwork |
| **P2** | Minimizer Partitioning Core (MINIM-01) | Canonical minimizer/signature, super-mers, exact per-bucket counting, globally sorted `.rkdb` output |
| **P3** | Disk-Backed Bounding (MINIM-02/03) | `--max-memory` for counting, spill, bucket admission + adaptive granularity, temp lifecycle reuse |
| **P4** | I/O & Parallel Pipeline | Producer/consumer overlap, multi-file/member decompression parallelism, chunk granularity, hasher swap **only if P1 evidence demands it** |
| **P5** | Dual-Surface Delivery & Verdict | Python routing through the new engine, 1-vs-N + old-vs-new golden matrix, KMC3 comparison (BENCH-V2-01), CI baseline regeneration |

P1 must come first: PROJECT.md Key Decisions records "v2.0 approach chosen from profiling evidence, not guesswork." Every "which phase" answer below assumes that ordering.

**v1.0 lessons already paid for — leverage, do not re-pay:**

| Lesson (paid in v1.0) | Where it lives now | What v2.0 must do with it |
|------------------------|--------------------|---------------------------|
| Exact-count contract is sacred (Chorus3 saturating 2-bit counters rejected) | `.planning/PROJECT.md` Out of Scope; `src/hash/table.rs:265-301` | Every new counter path stays exact u32, fail-loud at `u32::MAX` (Pitfall 8) |
| Parity gate before timing (caught the single-member gzip bug on the real full run) | `scripts/bench/bench.py:540-595`, incident note `:1291-1300`, fix commit `8102985` | Extend the gate to KMC3 with matched exact-count flags (Pitfall 18); run it on every new decoder (Pitfall 11) |
| 1-vs-N differentials vs committed goldens (PCOUNT-04) | v1.0 Phase 2 tests | Extend to old-path-vs-new-path differentials across the k/canonical matrix (Pitfall 9) |
| Byte-identity through refactors (DENSE-02 golden sha256 captured BEFORE refactor) | `tests/golden_sha256_tests.rs`, `tests/fixtures/` | Capture/keep goldens before the partitioning refactor; prove sortedness through consumers (Pitfall 15) |
| RAII temp lifecycle + TTL sweep; `panic="abort"` skips RAII | `src/database/temp_lifecycle.rs` (prefix `:45`, 7-day TTL `:82`, sweep `:135`) | Reuse the mechanism with a counting prefix AND extend the sweep selector (Pitfall 5) |
| Memory honesty: admission charges real bytes; peak = max(rss, phys_footprint); never mmap spill when RSS is the budget | v1.0 Phase 3 model; PROJECT.md Context | Same discipline for counting spill (Pitfall 7) |
| MSRV 1.80 is a hard gate (`is_multiple_of` incident: 8 pre-existing calls became clippy failures under `-D warnings`) | both `Cargo.toml` `rust-version`, `clippy::incompatible_msrv` | MSRV-audit every new dependency and API (Pitfall 17) |
| Benchmark honesty: true cache_state per rep, counterbalanced reps, medians, per-platform baselines from the CI runner class | `scripts/bench/`, `baselines/bench_baseline.{darwin,linux}.json` | Keep all of it; regenerate baselines only from CI artifacts (Pitfall 19) |
| PyO3: `py.detach` (not deprecated `allow_threads`); global allocator swap disqualified; installed `.so` is prebuilt | `pyo3/src/counter.rs:359-367`; backlog 999.2 | No GIL regressions; rebuild before pytest (Pitfalls 13, 19) |

---

## Critical Pitfalls

### Category A — Minimizer partitioning

### Pitfall 1: Canonical-unaware minimizer splits every non-palindromic k-mer's count

**What goes wrong:**
A k-mer and its reverse complement get different minimizers, land in different buckets, and are counted as two distinct keys with split counts. In canonical mode the output has up to ~2× the distinct k-mers and roughly half the per-key counts. This is the single most destructive bug possible in this milestone: it silently breaks the exact-count contract on *both* surfaces and invalidates every benchmark.

**Why it happens:**
The naive minimizer takes the lexicographic min over the m-mers of the forward strand only. The window set of `revcomp(kmer)` is the reverse-complemented window set in reverse order — the forward-strand minimum is not invariant under that transform. KMC-class tools explicitly select `min(m-mer, revcomp(m-mer))` per window so both strands agree (IJC 2020 §2.3; WABI 2022; PMC6280066 — MEDIUM, cross-checked). rustkmer's canonical form is `min(kmer, revcomp)` (`src/kmer/canonical.rs:72-82`); the minimizer must use the *same* orientation convention and the same `<=` tie-breaking, or palindromic m-mers and equal-pair ties drift.

**How to avoid:**
- Define the minimizer over canonical m-mers: for each window, `min(enc(m), revcomp(enc(m)))`, then take the window minimum with a deterministic tie-break (e.g., leftmost). One implementation, shared by partitioning and any bucket-local re-check.
- Property test (proptest, already a dev-dep): for random k-mers across k ∈ {1..64}, `minimizer(x) == minimizer(revcomp(x))`; include palindromes, homopolymers, and all-A/all-T edge cases.
- Differential: partitioned path vs current counter on the committed golden inputs, canonical AND non-canonical modes (non-canonical mode must still partition each distinct key to exactly one bucket — co-locating both strands is fine, splitting one key is not).
- Do this in P2's first plan, before any disk machinery exists, so the property is proven on the in-memory partitioner first.

**Warning signs:**
Distinct count ≈ 2× the current counter on the same canonical input; per-bucket count sums disagree with the global total; the bench parity gate fails with "jellyfish Distinct != rustkmer unique_kmers"; histograms show paired k-mers with complementary counts.

**Phase to address:** P2 (design + property tests), P5 (differential proof). Confidence: HIGH on mechanism (code + cross-checked literature).

---

### Pitfall 2: Bucket-local key representations leak into counts or output

**What goes wrong:**
KMC-class counters store bucket-local keys — the k-mer suffix after the minimizer, or a (signature, remainder) packing — to save space. If that bucket-local integer is fed to `KmerCounter::increment` or written to `.rkdb`, two distinct k-mers from different buckets alias onto one key, or the output file contains keys that decode to wrong sequences.

**Why it happens:**
The existing dense path narrows `u128 → u64` with only a `debug_assert!` guarding the high bits (`narrow_to_dense`, `src/hash/table.rs:223-232`, threat T-03-09). Release builds elide it. A bucket-local packing that puts signature bits in the high positions passes silently in release and merges counts of unrelated k-mers. The `.rkdb` entry writer expects the FULL canonical k-mer as u128 LE (`KmerEntry::write_to`, single writer in `src/database/format.rs`).

**How to avoid:**
- Make the bucket boundary a reconstruction point: decode the bucket-local key back to the full canonical u128 before it touches the counter, the sorter, or the writer. Keep the reconstruction in one function with a round-trip property test (`reconstruct(pack(x)) == x` for all k ≤ 64).
- Keep the T-03-09 `debug_assert!`; add a conservation test that runs in release (sum of per-bucket distinct keys == global distinct; spot-check decoded sequences against the input).
- Golden sha256 byte-identity (DENSE-02 discipline) catches any leaked packing in the output immediately — run it from the first P2 plan that writes a file.

**Warning signs:**
`debug_assert` fires in `cargo test` but release output "looks fine"; decoded k-mers from the new database contain impossible prefixes; distinct counts *shrink* vs the old path (aliasing merges keys); golden sha256 mismatch.

**Phase to address:** P2. Confidence: HIGH (code-anchored).

---

### Pitfall 3: One giant bucket defeats the memory bound (minimizer skew is severe on real genomes)

**What goes wrong:**
Bucket sizes are wildly non-uniform: published binning studies show max/mean bucket ratios up to ~80 and >90% of k-mers concentrating in ~50 minimizers on real data (Discount 2020; Gerbil/AdaOrder 2021; IIIT binning study — MEDIUM, cross-checked). Poly-A tails, adapter dimers, and low-complexity repeats all share a handful of minimizers. One bucket exceeds the RAM budget → OOM, or the "bounded" counter silently falls back to an unbounded path, or one rayon task runs for the entire second pass while other cores idle.

**Why it happens:**
Lexicographic minimizers systematically favor low-complexity m-mers (AAAA… sorts first). KMC2's signature rules exist precisely for this: exclude m-mers starting AAA or ACA, or containing AA internally (~11% smaller super-k-mer volume as a side effect). KMC3 additionally samples the input, builds a signature-frequency histogram, and packs signatures into a capped number of bins (~2000). A fixed `hash(minimizer) % n_buckets` scheme reproduces the skew.

**How to avoid:**
- Adopt signature-style filtering (KMC2 rules) OR frequency-aware signature→bin packing from a sampled pass (KMC3). Decide in P2 from a measured bucket histogram on the real CRR slice, not from theory.
- Per-bucket admission control in P3: estimate bucket size from the distribution pass; a bucket that exceeds the budget gets recursively re-partitioned (longer minimizer / secondary signature — this is exactly MINIM-03 "adaptive shard/prefix granularity").
- Log the bucket-size histogram (top-10, max/mean) every run at `--verbose`; warn when max/mean > 5 (v1.0 research already proposed this threshold for merge).
- Test with an adversarial input: synthetic poly-A-heavy reads + real adapter sequences. The CI synthetic generator (`scripts/bench/gen_synthetic.py`) should gain a low-complexity mode.

**Warning signs:**
Bucket file sizes span orders of magnitude; progress shows one bucket at 1% while others finish; RSS spikes during a single bucket's count phase; wall time dominated by one worker (flamegraph shows a single long `count_bucket` task).

**Phase to address:** P2 (signature design + histogram), P3 (admission + re-partition). Confidence: MEDIUM on the published ratios, HIGH that the failure mode applies here.

---

### Pitfall 4: Super-mer boundary and read-end k-mers lost or double-counted

**What goes wrong:**
Super-mer construction (merging consecutive k-mers that share a minimizer) drops or duplicates windows at super-mer joins, at read ends, at N-interrupted runs, or for reads shorter than the minimizer window. Counts are off by small amounts that only show up on real data — the worst kind of exact-count bug.

**Why it happens:**
Off-by-one at the joins: consecutive super-mers are adjacent in window space; the boundary window belongs to exactly one of them. Reads shorter than `k + w - 1` have fewer than w windows — the "window" is the whole read and must still yield every one of its `len - k + 1` k-mers. The current extractor's semantics are pinned: `for i in 0..=(seq.len() - k)`, windows containing invalid characters are *skipped* (not stripped), sequences shorter than k contribute zero (`process_one_record`, `src/cli/commands/count.rs:377-411`). Edge k-mers appear in only one window (selection probability 1/w vs ~2/(w+1) — PeerJ syncmers; Zheng review) — for *counting* this is a balance issue, not correctness, because the minimizer is a pure function of the k-mer; correctness breaks only if the implementation special-cases edges inconsistently. Also: minimizer length m must be ≤ k — the API supports k = 1..64 (`KmerCounter::new`), so small-k inputs need a defined fallback (shorter m, or a direct dense table for tiny k), not a panic.

**How to avoid:**
- Conservation invariant as a first-class test (v1.0 merge discipline: two phase-independent conservation checks, not a tautology): for every read, `sum(windows assigned to buckets) == number of valid windows per the current extractor`. Run it against the naive per-window extractor on an edge matrix: len ∈ {k-1, k, k+1, k+w-2, k+w-1, k+w}, N at start/middle/end, all-N, lowercase, palindromes, k ∈ {1, 5, 21, 31, 32, 33, 64}.
- Reuse `process_one_record`'s window semantics verbatim in the partitioner (or better: extract it into the shared core so there is literally one definition — see Pitfall 10).
- If reads are split into segments for parallelism, overlap segments by a full window length and deduplicate by window identity (Zheng review) — or simpler, never split below record granularity (the current CHUNK_SIZE design already keeps records whole).

**Warning signs:**
`total_kmers` differs from the old path by an amount proportional to read count (boundary loss) or to N count (semantic drift); conservation test fails only on short reads; k < m inputs panic or silently count zero.

**Phase to address:** P2. Confidence: HIGH on the code semantics, MEDIUM on the literature framing.

---

### Category B — Disk-backed counting

### Pitfall 5: Reinventing temp-file lifecycle — orphan accumulation and ENOSPC

**What goes wrong:**
Disk-backed counting writes hundreds of bucket files. A crash (SIGKILL, OOM, panic under `panic="abort"`) leaves them behind; retries hit "No space left on device"; the disk fills with orphans. KMC-class temp usage is enormous — up to 350 GB for GIAB (WABI 2022), ~596 GB temp for a 729 Gbase human dataset at k=28 (NUS notes), 32 GB RAM / 389 GB temp for 614 GB input (KMC README) — MEDIUM, cross-checked. ENOSPC mid-count is a when, not an if, on dev laptops.

**Why it happens:**
v1.0 already solved this for merge: process-unique `rustkmer-merge-<rand>/` subdirs, RAII cleanup, and a 7-day-TTL startup sweep that also reclaims loose chunk files (`src/database/temp_lifecycle.rs:45,82,135`). The sweep's selector is **prefix-based** — a new counting path that writes `rustkmer-count-*` (or worse, generic names) gets RAII only, and RAII does not run under `panic="abort"` (release profile) or SIGKILL. The existing `DiskOverflow` (`src/hash/overflow.rs`) is a trap for the unwary: its `Drop` only flushes/closes (`:149-153`) — it never deletes the directory, it is not registered with any sweep, its keys are u64-only (breaks k > 32), and it `sync_all`s every file (`:95`). It predates the v1.0 lifecycle discipline.

**How to avoid:**
- Generalize `temp_lifecycle.rs`: add a counting prefix constant paired with the sweep selector exactly like `MERGE_TEMP_PREFIX` / `CHUNK_FILE_PREFIXES` (the doc comment there already warns the prefix is the sweep's only selector). Reuse `create_merge_temp_subdir`'s pattern and `sweep_stale_merge_dirs`' TTL logic — do not write a second lifecycle module.
- Pre-flight disk estimate from the distribution pass (super-mer volume ≈ input volume, KMC-class) + a guardrail refusal before writing (the bench harness already has a disk guardrail to copy).
- ENOSPC mid-run: abort loudly, preserve shards for diagnosis, log paths — the v1.0 merge precedent ("failed prefix buckets abort the merge loudly with their shards preserved and logged").
- Tests: SIGKILL orphan → next-run sweep reclaims; ENOSPC injection (small tmpfs / RLIMIT_FSIZE) → clean error, no silent truncation; sweep never deletes a *live* run's files (TTL test).

**Warning signs:**
`df` fills across runs; orphan dirs after a killed run; sweep log line reports 0 files while orphans exist (prefix mismatch); `DiskOverflow` appearing in a v2 diff.

**Phase to address:** P3. Confidence: HIGH (code + v1.0 precedent; KMC disk figures MEDIUM).

---

### Pitfall 6: Disk I/O becomes the new bottleneck — fsync overkill and fd exhaustion

**What goes wrong:**
The two-pass design writes and re-reads the whole dataset; I/O cost is the dominant performance factor for disk-based counters (Bioinformatics btab797 — MEDIUM). Per-file or per-chunk `fsync` multiplies wall time for zero benefit (temp files are regenerable). Hundreds of simultaneously-open bucket writers hit the macOS default file-descriptor limit (256) — KMC's own docs tell macOS users to raise `ulimit -n 2048` because it creates "hundreds of intermediate files."

**Why it happens:**
Durability habits copied from database code (`DiskOverflow::close_current_file` does `sync_all`, `overflow.rs:95`); one-open-writer-per-bucket designs with 4^m buckets; assuming SSD bandwidth is free while 16 threads append interleaved to hundreds of files (random-ish write patterns).

**How to avoid:**
- No `fsync` on temp bucket files; `flush` at close only. Durability is required for the FINAL `.rkdb` exactly as much as it is today (the current count path does not fsync either — keep parity, don't "improve" it silently).
- Buffered sequential appends; cap concurrently-open writers (LRU writer pool or per-worker bucket buffers flushed in large blocks — measure, don't guess). Keep bucket count in the hundreds (KMC3 caps bins ~2000), not 4^m.
- Measure with `iostat -x 1` during P3 development; if pass-2 I/O wait dominates, the answer is bigger buckets / fewer passes, not more threads.
- Handle EMFILE explicitly with an actionable error message (and document the ulimit guidance for macOS in the counting docs).

**Warning signs:**
`iostat` shows 100% utilization with low throughput; flamegraph time in `sync_all`/`fsync`; "Too many open files" errors on macOS only; pass 2 slower than pass 1.

**Phase to address:** P3 (design), P4 (I/O tuning). Confidence: HIGH on mechanisms, MEDIUM on KMC operational figures.

---

### Pitfall 7: mmap spill under an RSS budget, and dishonest admission accounting

**What goes wrong:**
Spill files are memory-mapped "for speed"; mapped pages count into RSS, the measured peak blows the budget, and the CI memory gate fails — or worse, the budget check passes on paper while the process actually OOMs. Alternatively, admission control charges fantasy bytes-per-entry and the "bounded" counter exceeds the cap on real data.

**Why it happens:**
This is a pre-registered v1.0 lesson (PROJECT.md Context, Chorus3 investigation): "never mmap spill files when RSS is the budget" and "peak measured as max(rss, phys_footprint)". The merge admission model charges real measured bytes (96 B/k-mer in-memory, 32 B/k-mer streaming; the counter models 24 B hash overhead + key + 4 B count, `src/hash/table.rs:16-19`). A new counting path that estimates "k-mer = 8 bytes" and forgets table overhead, bucket buffers, and the sort arena repeats the v1.0 OOM-on-estimate bug in a new place.

**How to avoid:**
- Read spill with `BufReader`, never mmap, when RSS is the budgeted resource. (mmap remains fine for read-only query paths where it already lives.)
- Charge every component: per-bucket hash/sort arena, write buffers, decompression chunk, in-flight super-mer buffers. Reuse the merge admission pattern: estimate → hard route, not suggestion.
- Pre-register the peak gate before measuring: max(rss, phys_footprint), measured live (the v1.0 bounded-memory tests already do red/green RSS assertions — copy that harness shape for counting).

**Warning signs:**
Measured peak ≈ budget + spill-file size (mmap signature); admission estimate vs live RSS diverge >20% on a 200M-record test; memory gate passes on Linux but fails on macOS (phys_footprint vs RSS divergence).

**Phase to address:** P3. Confidence: HIGH (v1.0 measured precedent).

---

### Category C — Exact-count preservation

### Pitfall 8: Saturation / overflow semantics drift in the new counters

**What goes wrong:**
A new per-bucket counter uses `saturating_add`, a smaller counter type (u8/u16 "like KMC"), or wrapping arithmetic. High-coverage k-mers (poly-A, adapters, rRNA, mitochondrial) clip silently; the exact-count contract dies without any error. Note the contrast: **KMC's default `-cs 255` clips counters at 255** (KMC issue #136, official source — MEDIUM cross-checked) — "KMC does it" is not a defense; rustkmer's product is exact u32.

**Why it happens:**
Space pressure tempts small counters (the Chorus3 2-bit saturating design was researched and REJECTED for exactly this reason, PROJECT.md Out of Scope). The current semantics are precise and pinned: `increment` returns `Err` when a count would exceed `u32::MAX`, with a verbatim message (`src/hash/table.rs:265-301`); `total_kmers` counts only successful increments (WR-03). Merge's `saturating_add` is a known carried debt (WR-02), not a precedent to copy. Cross-chunk summation in pass 2 (`count += chunk_count`) is a NEW overflow site that does not exist today.

**How to avoid:**
- u32 exact counters everywhere; the overflow predicate and the verbatim error message stay identical on every path (the message is contract-pinned by tests).
- Pass-2 summation uses checked arithmetic and surfaces the same overflow error — never `saturating_add`, never silent wrap.
- Boundary tests at `u32::MAX - 1` / `u32::MAX` / overflow-attempt, per bucket and across chunk sums (extend the v1.0 merge tests that proved 2,000,000 and 16,777,216 round-trips).
- Detection statistic: a histogram spike at exactly the counter maximum is the classic saturation fingerprint — add it to `stats` output review during verification.

**Warning signs:**
Counts plateau at 255 / 65535 / 4294967295; totals disagree between 1-thread and N-thread runs only on high-coverage inputs; the overflow error message text changes (tests catch it — do not "fix" the tests).

**Phase to address:** P2/P3 (implementation), P5 (boundary proof). Confidence: HIGH.

---

### Pitfall 9: Double-counting across buckets or passes; merge accumulation drift

**What goes wrong:**
The same canonical k-mer is counted in two buckets (partition function not disjoint), or a super-mer straddling a chunk boundary is processed twice, or pass 2 adds a bucket's partial counts twice. Totals inflate; distinct counts may even look right while per-key counts are wrong.

**Why it happens:**
Two-pass pipelines have three independent summation boundaries (windows→super-mers, super-mers→buckets, bucket chunks→final) and each is an off-by-one opportunity. Canonical drift (Pitfall 1) is one cause; nondeterministic rayon fold/split boundaries (rayon docs: split points are nondeterministic — LOW, official docs) are another if fold accumulators are not order-independent.

**How to avoid:**
- Disjointness property test: for random k-mers, `bucket(canonical(x))` is a single value; for random reads, every valid window appears in exactly one super-mer (conservation, Pitfall 4).
- Two phase-independent conservation checks (the v1.0 merge lesson: the "can-never-fire integrity tautology" was replaced by checks that could actually fail): (a) sum of per-bucket window counts == producer's window count; (b) sum of final counts == `total_kmers` atomic.
- The full differential matrix in P5: old-path vs new-path AND `--threads 1` vs N, on committed golden baselines, across k ∈ {21, 31, 32, 33, 64} × canonical {on, off} (PCOUNT-04 discipline extended with an old-vs-new axis).

**Warning signs:**
`total_kmers` > sum of `len - k + 1` valid windows; new-path totals exceed old-path totals on the same input; 1-vs-N differential fails only at specific chunk sizes.

**Phase to address:** P2 (invariants), P5 (matrix proof). Confidence: HIGH.

---

### Pitfall 10: Extraction-semantics drift between paths — INCLUDING a divergence that already exists between CLI and Python

**What goes wrong:**
The partitioned path, the old path, and the Python path disagree about what a "counted k-mer" is. **Verified in code today:** the CLI skips windows containing non-ACGT characters (`process_one_record`, `count.rs:385-408` — the window is dropped, flanks are NOT joined), while the PyO3 file paths **strip non-ACGT bytes and concatenate the flanks** before extraction (`pyo3/src/counter.rs:737-741` FASTA, `:798-801` FASTQ: `.filter(|&b| matches!(b.to_ascii_uppercase(), b'A'|b'C'|b'G'|b'T'))`). On an N-containing read the Python surface counts chimeric k-mers spanning the N that the CLI never counts. Real Illumina reads contain Ns. v2.0's acceptance ("byte-identical optimized counts on BOTH surfaces") is ill-defined until this is surfaced and decided.

**Why it happens:**
The two surfaces grew separate extraction loops (v1.0 parallelized the CLI path; the PyO3 file path kept its own sequential line-based loop). A rolling 2-bit encoder (a likely v2.0 optimization) adds a third semantics risk: the rolling value must be masked to 2k bits and the valid-window run counter RESET at every N and every record boundary, or it emits k-mers spanning invalid bases — silently reproducing the Python bug in the CLI.

**How to avoid:**
- P1 must run a CLI-vs-Python differential on N-containing and lowercase reads, record the divergence, and surface the semantics decision to the user (the v1.0 WR-04 precedent: user-visible behavior changes are surfaced, never silently "fixed"). The CLI semantics are the ones the jellyfish parity gate validated — they are the reference.
- Extract ONE window-extraction function into the shared core; CLI, Python, and the partitioner all call it (this is also the delivery vehicle for Pitfall 16).
- If a rolling encoder is introduced: differential-test it against the per-window `encode_kmer_bytes_u128` on the edge matrix (N at every position, record boundaries, lowercase, k ∈ {1..64}) before it replaces anything.

**Warning signs:**
CLI vs Python distinct/total differ on the same real-read file (they do today, on N reads); rolling-encoder counts exceed per-window counts by ≈ (N count × k); parity vs jellyfish holds on synthetic ACGT-only data but fails on real reads.

**Phase to address:** P1 (measure + decide), P2 (shared core). Confidence: HIGH (direct code observation — this is a finding, not a hypothesis).

---

### Category D — Parallelism

### Pitfall 11: Single-threaded decompression masks every counting gain — and the current loop doesn't even overlap

**What goes wrong:**
Counting gets 5× faster and wall time barely moves, because gzip decompression is single-threaded (D-02) AND the producer loop **blocks during each chunk's `par_iter`** (`count.rs:481-506`: fill 4096 records → synchronous `try_fold/try_reduce` → clear → resume reading). Decompression and counting alternate; total ≈ T_decompress + T_count, never max(...). Amdahl caps the visible win at the decompression fraction. Worse, a "fix" that swaps in a parallel decoder can silently corrupt input: rustkmer already shipped a single-member gzip bug that read only member 1 of a concatenated-gzip input — caught by the parity gate on the first full-run attempt (bench.py:1291-1300, fix `8102985`, `MultiGzDecoder` at `src/io/fastq.rs:78`).

**Why it happens:**
Sequential `bio` readers over `GzDecoder` were the v1.0 scope; overlap was deferred. Teams reach for "use pigz" — but pigz's man page is explicit that decompression cannot be parallelized without specially prepared streams; pigz parallelizes *compression* only (MEDIUM, man page + rapidgzip paper). True parallel inflate of arbitrary gzip needs speculative deflate-block discovery + 32 KiB window reconstruction (rapidgzip, arXiv 2308.08955), whose block finder produces false positives that must be validated by trial decode — a new dependency with real correctness surface.

**How to avoid:**
- P1 measures the split FIRST: same input gz vs pre-decompressed, record T_decompress and T_count separately. This number decides how much of the 5× gap counting work can even address, and whether P4 should precede P2.
- Cheapest safe wins, in order: (1) producer/consumer pipeline — a bounded queue decouples the reading thread from rayon workers (overlap without any new decoder); (2) file-level parallelism across the split parts / multiple inputs; (3) member-level parallelism for concatenated-gzip files; (4) only then consider a rapidgzip-class crate (MSRV + correctness audit, Pitfall 17).
- ANY new decoder path must pass: the multi-member regression test, the parity gate on the measured input, and a concatenated-member fixture (two gz members whose second member alone changes the counts).

**Warning signs:**
CPU utilization sawtooth (one core busy, then all cores, then one); gz input runs ≈ uncompressed run + constant; a "faster" build reports suspiciously small `total_kmers` (prefix-only read — the 8102985 fingerprint); `--threads` scaling flat on gz but linear on plain FASTQ.

**Phase to address:** P1 (measure), P4 (fix). Confidence: HIGH on the code structure, MEDIUM on decoder ecosystem claims.

---

### Pitfall 12: Rayon granularity, per-chunk barriers, and thread-precedence regressions

**What goes wrong:**
Tiny tasks (one 150 bp record per task) drown in work-stealing overhead; giant tasks (one bucket per task, skewed sizes — Pitfall 3) leave cores idle; a new partitioned engine builds its OWN thread pool and ignores the `--threads > RUSTKMER_THREADS > RAYON_NUM_THREADS > num_cpus` precedence chain (`resolve_thread_count`, `count.rs:802-847`), or nests manual threads inside the global pool and oversubscribes (the v1.0 Pitfall 14 reborn).

**Why it happens:**
The global pool is built ONCE per process (`count.rs:100-103`; `PyCounter::new` `counter.rs:188-197` — second construction is logged and ignored, IN-04). A v2 engine that calls `ThreadPoolBuilder::build_global` again, or creates a private pool sized from `num_cpus` directly, silently breaks the documented precedence and the Python `threads=` contract. rayon's `with_min_len`/`with_max_len` are hints, not guarantees (official docs — LOW single-fetch); fold/reduce split points are nondeterministic, so accumulators must be order-independent.

**How to avoid:**
- Route every new pool/thread decision through `resolve_thread_count` (CLI) and the existing `PyCounter::new` resolution (Python); keep the build-once idiom and the IN-04 warn.
- Keep record-chunk batching (CHUNK_SIZE=4096 is the measured v1.0 starting point); if task granularity is tuned, sweep it in P4 with the bench harness, not by intuition. Bucket-level tasks in pass 2 should be sub-split when skewed (Pitfall 3's re-partition also fixes parallelism).
- Differential `--threads 1` vs N stays green at every step (PCOUNT-04) — it catches both lost updates and precedence breakage.
- Do not nest a second parallel runtime inside rayon workers; one pool, work-stealing handles the rest.

**Warning signs:**
`--threads 64` slower than `--threads 16`; `top` shows more busy threads than the flag requested; scaling collapses after 4-8 threads; a second `PyCounter(threads=...)` in one process changes nothing (expected today — must stay documented, not become a surprise).

**Phase to address:** P2/P4. Confidence: HIGH on code contracts, LOW on the rayon doc nuances (official docs, single fetch).

---

### Pitfall 13: GIL and PyO3 regressions in the new engine

**What goes wrong:**
A new counting entry point spawns rayon workers without `py.detach` → deadlock (worker blocks on GIL acquisition while the calling thread holds it — the official PyO3 parallelism guide's central warning, corroborated by the in-repo rationale at `pyo3/src/counter.rs:359-367`). Or workers touch Python objects → serialization on the GIL erase the speedup. Or someone reintroduces `allow_threads` (deprecated since 0.26) or a global allocator swap (disqualified for the Python surface — PROJECT.md).

**Why it happens:**
The partitioned engine adds new call paths (bucket workers, spill I/O threads) that were not covered by v1.0's detach audit. Closures that capture `Bound<'_, PyAny>` instead of owned Send types compile-fail or force GIL re-acquisition. Progress callbacks tempt calling Python from workers.

**How to avoid:**
- Every PyO3 method that spawns threads or blocks on I/O wraps the work in `py.detach`; closures capture only owned `Send` Rust types (the existing `process_*_file_on_counter` pattern is the template).
- No Python callbacks from workers; progress goes through the Rust `log` facade / atomics polled from the Python side.
- Keep the no-global-allocator rule; keep `py.detach` (not `allow_threads`).
- Rebuild the extension before every pytest run (`maturin develop --release`) — the installed `.so` is prebuilt and stale-site-packages shadowing is a known backlog item (999.2). Assert the loaded module's version/commit in the test session header.

**Warning signs:**
Python count hangs with one core at 100% (deadlock fingerprint); pytest passes but benchmarks show no speedup (stale `.so`); `PyCounter` methods that used to release the GIL now hold it (thread-scaling test in `pyo3/tests` goes flat).

**Phase to address:** P5 (delivery), every phase's verification. Confidence: HIGH (official guide + in-repo corroboration).

---

### Category E — Faster hasher

### Pitfall 14: Hasher swap without evidence — quality, shard balance, and iteration order

**What goes wrong:**
`ahash` is replaced with a "faster" hasher and (a) the win is ~0 because hashing was never the bottleneck, (b) structured 2-bit-packed keys cluster SwissTable probe groups AND DashMap shards, reintroducing v1.0's lock contention through the back door, or (c) iteration order changes and `--no-sort` output / any order-sensitive golden drifts.

**Why it happens:**
The Chorus3 small-k result (direct-address ~5× over DashMap at k=17) is *hypothesis-grade* for rustkmer — it was measured on saturating semantics at a different k on a 135 Mbp reference (PROJECT.md explicitly requires validation on the real workload). Meanwhile the evidence says ahash is already near-optimal for integer keys: rustc measured fxhash→ahash as 1-4% SLOWER (Rust Performance Book — MEDIUM cross-checked). k=21 keys are 42-bit structured integers; SwissTable uses top hash bits for control bytes and low bits for bucket index, and hashbrown's own benchmarks show 4.2-6.75× swings between hashers on serial/high-bit-heavy keys (hashbrown README — MEDIUM). DashMap derives its shard index from the hash, so weak avalanche = hot shards = the v1.0 RwLock bottleneck reborn. ahash is per-process randomly seeded; DashMap iteration is already run-to-run nondeterministic (the D-09 default-sort rationale, `count.rs:66-71`) — the default sort is what protects `.rkdb` byte-identity, not the hasher.

**How to avoid:**
- P1 profiles hashing cost on the REAL k=21 workload (flamegraph + `perf stat` cache misses; a synthetic key-distribution microbench of candidate hashers on actual counted keys). No swap without that evidence — user directive.
- If evidence supports a swap: choose an SMHasher-passing hasher (wyhash/foldhash class; rustc-hash 2.x changed its algorithm and has MSRV 1.77 — verify any candidate's MSRV ≤ 1.80), measure per-shard entry-count histograms on real keys (max/mean shard ratio), and keep the default sort untouched.
- Never weaken the hasher to fxhash-class for 2-bit keys without the shard histogram; "fast" hashers are fast precisely because they skip mixing.
- Golden fixtures are sorted-mode only; if any `--no-sort` fixture exists, treat order drift as a surfaced decision, not a test update.

**Warning signs:**
Hasher swap yields <5% on the full pipeline (Amdahl — hashing wasn't hot); per-shard histogram max/mean > 2; throughput collapses at higher thread counts only (shard contention); `--no-sort` output bytes change between builds.

**Phase to address:** P1 (decide), P4 (apply only if evidence). Confidence: MEDIUM (cross-checked ecosystem data), HIGH on the iteration-order/default-sort mechanics (code).

---

### Category F — Integration & migration

### Pitfall 15: Breaking `.rkdb` v2 byte-identity — bucket order is NOT sorted order

**What goes wrong:**
Partitioned counting emits counts in bucket order; concatenating buckets produces a file that is NOT globally ascending by canonical key. If the header still says `sorted: true`, the binary-search consumers (`src/database/query.rs`, prefix query) silently return wrong answers. Even with a correct sort, header-field drift (flags, offsets, totals) breaks the golden sha256 fixtures and downstream compatibility.

**Why it happens:**
v1.0 merge learned this exact lesson: first-4-bases prefix bucketing concatenates ascending ONLY because the first bases are the high bytes of the encoding (the CR-01/WR-03 fixes; "sorted: true header is truthful by construction — proven by querying through both binary-search consumers"). **Minimizer order has no relationship to key order** — the prefix trick does not transfer. The header literal is pinned (`count.rs:725-736`: `data_offset=42`, `index_offset=0`, `total_kmers`/`unique_kmers` = record count, `file_size` in-memory only) and the entry writer is the single source of truth in `format.rs` (FOUND-03). Note the IN-03 name collision: `KmerCounter::total_kmers` = SUM of counts, `DatabaseHeader::total_kmers` = RECORD count (`table.rs:460-473`) — a new writer that "fixes" the header to the sum breaks byte-identity.

**How to avoid:**
- Final stage = k-way merge of per-bucket sorted runs into one globally ascending stream (reuse the v1.0 `streaming_merge.rs` VecDeque-backed k-way merge — it exists, is record-aligned and tail-carrying) or an external sort. Stream it; do not materialize (Pitfall in Performance Traps: `get_all_counts`).
- Prove sortedness through BOTH binary-search consumers, not by inspecting the flag (v1.0 pattern); golden sha256 byte-identity vs the current counter's output on the committed fixtures, captured BEFORE the refactor lands.
- Header semantics frozen: same literals, same single writer. Any format change is a surfaced decision per PROJECT.md Constraints — not a side effect.

**Warning signs:**
Golden sha256 mismatch; `query` returns None for k-mers that `dump` shows present; prefix query results change; header `sorted` flag true while a linear scan finds a descending pair.

**Phase to address:** P2 (output stage), P5 (proof). Confidence: HIGH.

---

### Pitfall 16: Dual-surface divergence — the CLI gets the win, Python doesn't

**What goes wrong:**
The new engine is wired into `execute_count` only. `pyrustkmer` keeps its own file-counting loops — which are **sequential today** (verified: `process_fasta_file_on_counter` / `process_fastq_file_on_counter`, `pyo3/src/counter.rs:700-809`, contain no rayon parallelism at all; there is no `par_iter` anywhere in `pyo3/src/`). The CLI closes the k=21 gap; Python stays ≥5× slower (worse than the CLI, since it never got the chunked parallel path). The milestone acceptance explicitly includes the Python surface — this fails it.

**Why it happens:**
The shared core is the *table* (`KmerCounter`), but the *pipelines* diverged: CLI has chunked rayon + bio readers; Python has line-based sequential loops + its own extraction semantics (Pitfall 10). Swapping the table implementation under both does not deliver pipeline wins to Python. v1.0 merge solved the identical problem with a shared path-shaped entry point (`merge_databases_to_path`) that both front-ends call — the counting equivalent does not exist yet.

**How to avoid:**
- P1/P2 build ONE counting entry point in the core (input paths → extraction → counting → output), consumed by `execute_count` AND `PyCounter::add_from_*`. The PyO3 layer becomes argument validation + `py.detach` + error mapping, nothing else.
- P5 adds a Python-surface benchmark to the gate (revive the commented-out `python_cli_comparison` criterion bench or a pytest-benchmark equivalent) with its own committed baseline — "no Python regression" must be measured, not asserted.
- Public API frozen: `PyCounter(kmer_length, canonical, initial_capacity, threads)` signatures and error types unchanged; `--size` may become advisory for the partitioned engine but must still parse (document, don't remove).

**Warning signs:**
CLI benchmark improves while the Python benchmark is flat; `pyo3/tests` still pass (they assert correctness, not speed — that's the trap); grep shows counting logic still living in `pyo3/src/counter.rs` after P2.

**Phase to address:** P1 (groundwork), P2 (shared entry point), P5 (measured proof). Confidence: HIGH (code-verified).

---

### Pitfall 17: MSRV and dependency traps

**What goes wrong:**
New code or a new dependency uses post-1.80 APIs and the `clippy::incompatible_msrv` gate (`-D warnings`, both crates, 3-OS CI) turns the PR red — the `is_multiple_of` incident (8 pre-existing calls, stable 1.87) is the paid precedent. Or a dependency drags in a global allocator, a newer PyO3, or an MSRV > 1.80 transitively.

**Why it happens:**
Dev hosts run current stable, so local `cargo clippy` passes while the MSRV gate fails. Attractive v2.0 dependencies (rapidgzip-class decoders, foldhash, wyhash, CQF crates) have unvetted MSRVs; rustc-hash 2.x is MSRV 1.77 (OK) but that was verified, not assumed. The constraint is explicit: work within the established dependency set (PROJECT.md Constraints); a global allocator is disqualified for the PyO3 surface.

**How to avoid:**
- Every phase's verification runs clippy with the 1.80 toolchain (or the MSRV-aware lint as CI does) on BOTH crates — not just the dev-host stable.
- Before adding any crate: check `rust-version` in its manifest, its transitive tree (`cargo tree`), and that it does not set `#[global_allocator]` or bump PyO3. Prefer std/existing-dep solutions (a bounded-queue pipeline needs no new crate; `std::sync::mpsc`/existing parking_lot suffice).
- New std APIs: check stabilization against 1.80 before use (the lint catches most, but not all patterns).

**Warning signs:**
CI clippy red while local green; `cargo tree -i pyo3` shows two PyO3 versions; a dependency's README mentions allocator features.

**Phase to address:** All phases; P4 especially (new-dep pressure). Confidence: HIGH.

---

### Category G — Measurement

### Pitfall 18: Benchmark unfairness — KMC3's defaults are NOT exact counting

**What goes wrong:**
The BENCH-V2-01 KMC3 comparison runs `kmc -k21 ...` with defaults and either (a) the parity gate "fails" and someone weakens rustkmer to match, or (b) the gate is skipped and the timing comparison is meaningless. Verified against the official KMC source (`kmc_CLI/kmc.cpp` usage text) and issue #136 (MEDIUM, cross-checked): **`-ci` defaults to 2** (singleton k-mers excluded), **`-cs` defaults to 255** (counters SATURATE at 255), **`-cx` defaults to 1e9** (ultra-frequent k-mers excluded), `-m` defaults to 12 GB RAM, `-sm` strict-memory mode is off. rustkmer counts every k-mer exactly into u32. These tools are not counting the same thing out of the box.

**Why it happens:**
The v1.0 parity discipline (one `BenchmarkConfig` drives both command lines, `bench.py:172-173`) was built for jellyfish, whose matched settings are already pinned (generous `-s`, `-C` canonical, matched `-t`). KMC3 has three independent filtering/clipping knobs that jellyfish doesn't, and its counter width scales with `-cs` — so configuring it for exact u32 counting CHANGES its memory/speed profile. Comparing rustkmer-exact against KMC-default is comparing different products.

**How to avoid:**
- Extend `BenchmarkConfig` with a KMC3 member that derives: `-ci1 -cx4294967295 -cs4294967295`, matched `-t`, canonical on, `-m` set to the agreed budget (and record whether `-sm` is used). Re-verify defaults via `kmc` help at benchmark time (the source checked here is master, not a pinned release).
- Parity gate BEFORE any timing, on the measured input itself (the existing gate's contract: exit 0 parity / 1 mismatch / 2 methodology) — a KMC3 mismatch is a methodology finding, never a reason to touch rustkmer's semantics.
- Record the config honestly in the report: "KMC3 with u32 counters and no count filtering" is a different (fair) comparison than KMC3 defaults, and the report must say which ran. Note KMC3's disk-backed nature: its temp disk usage is part of its cost — record temp-dir size and disk class.

**Warning signs:**
KMC3 distinct count < rustkmer unique_kmers by roughly the singleton fraction; KMC3 max count == 255; parity gate skipped "to save time"; KMC3 numbers look dramatically better than published exact-count benchmarks.

**Phase to address:** P5. Confidence: MEDIUM (official source + issue cross-check; re-verify at run time).

---

### Pitfall 19: Profiling a stale binary, warm cache, or a non-representative slice

**What goes wrong:**
P1's root-cause profile measures the wrong thing: a stale release binary (or stale prebuilt `.so` — backlog 999.2's site-packages shadowing), a warm page cache (decompression/IO fraction collapses), a head-of-file slice (one flowcell region, unrepresentative N/error/poly-A profile), or synthetic reads (no adapter dimers, no quality decay, no low-complexity skew — exactly the features that drive k=21 behavior and bucket skew). The architecture decision then rests on garbage evidence — violating the user's "evidence before architecture" directive in the most expensive way.

**Why it happens:**
v1.0 paid for every one of these: a dev-host baseline breached CI thresholds (→ per-platform baselines bootstrapped from the CI runner class, `baselines/bench_baseline.{darwin,linux}.json`); cold-cache purge was unavailable (→ honest per-rep `cache_state` recording, "PARTIALLY satisfied" stated); the first full run was halted by the parity gate (→ timing never trusted before parity). Profiling is benchmarking with the same failure modes plus one more: attribution (decompression vs hashing vs memory bandwidth vs rayon scheduling).

**How to avoid:**
- Fingerprint every profile artifact: binary path + sha256 + git commit + build profile; for Python, the loaded module's `__file__` + version, asserted after `maturin develop --release`. The bench harness already records binary path and harness commit — extend the same discipline to P1's profiling notes.
- Attribution runs: gz vs pre-decompressed same input (isolates decompression); `--threads 1` vs N (isolates parallel efficiency); uncompressed + pre-encoded synthetic keys (isolates hashing/table cost); real CRR slice vs synthetic (isolates distribution effects). Record true cache_state per rep; counterbalanced reps; medians.
- Slices are random subsamples of records (not `head`), large enough to stabilize the distinct-k-mer curve; the degradation ladder stays honest about what each tier can and cannot show.
- P1's deliverable is a written attribution table (fraction of wall time per component, with evidence) that P2-P4 scope decisions cite. If the table says decompression dominates, P4 goes first — the roadmap must allow that reordering.

**Warning signs:**
Profile totals don't match the bench harness's wall time for the same input; "hot" functions vanish after a rebuild; slice-based distinct counts extrapolate linearly (they shouldn't — distinct curves saturate); Python profile shows an old version string.

**Phase to address:** P1 (primary), P5 (final verdict). Confidence: HIGH (v1.0 measured precedent).

---

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Small/saturating counters (u8/u16/2-bit) per bucket | Big memory win | Breaks the exact-u32 contract; the product's core value | **Never** (Chorus3 precedent, PROJECT.md Out of Scope) |
| CQF as the counting structure without exact-mode proof | Memory-efficient, cache-friendly | A quotient filter is approximate membership; false positives corrupt counts unless an exact counting variant with full remainders + verification is used | Only with an exactness proof on the golden matrix; training-knowledge claim — verify at architecture decision (LOW) |
| Reuse `DiskOverflow` as-is for spill | Code already exists | No deletion on Drop, no sweep registration, u64-only keys, per-file fsync — orphan + k>32 + perf bugs | Prototype throwaway only; P3 must use `temp_lifecycle.rs` |
| Skip the final global sort, set `sorted: false` | Saves the k-way merge stage | Breaks byte-identity goldens; binary-search consumers disabled; user-visible break | **Never** as default; only via explicit surfaced decision |
| Silently "fix" the Python N-stripping semantics | Surfaces agree | Changes counts for existing Python users without consent | **Never** silently — surface as a decision (WR-04 precedent), then fix in the shared core |
| Hasher swap without P1 evidence | Feels like progress | Possibly zero win, shard imbalance risk, iteration-order drift | **Never** (user directive: evidence before architecture) |
| fsync on temp buckets "for safety" | Crash-durability illusion | Multiplies wall time; temp data is regenerable | **Never** for temp; final output keeps today's semantics |
| mmap spill files | Easy random access | RSS accounting blows the budget (v1.0 pre-registered lesson) | **Never** when RSS is the budgeted resource |
| Update golden fixtures to make the diff green | Unblocks CI | Destroys the only byte-identity evidence | **Never** — goldens change only by explicit decision with old-vs-new differential |

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| `.rkdb` writer | Inlining a second header/entry writer in the new engine | Delegate to `DatabaseHeader::write_to` / `KmerEntry::write_to` in `format.rs` (FOUND-03 single source); header literals frozen (`count.rs:725-736`) |
| Binary-search consumers | Trusting the `sorted` flag | Prove ascending order by querying through `DatabaseQuery` AND prefix query (v1.0 merge pattern) |
| PyO3 GIL | Spawning workers without `py.detach`; capturing `Bound` types | detach + owned Send captures (`counter.rs:359-367` template); no Python callbacks from workers |
| rayon global pool | Second `build_global` or private pool bypassing precedence | Build-once idiom + `resolve_thread_count` chain; IN-04 warn on re-init |
| Temp lifecycle | New prefix without extending the sweep selector | Prefix constant paired with sweep (temp_lifecycle.rs doc warns: prefix is the only selector) |
| gzip input | Single-member decode; assuming pigz parallelizes reads | `MultiGzDecoder` semantics preserved (regression 8102985); pigz decompresses sequentially |
| Bench parity gate | Timing first, parity later; KMC3 defaults | Parity on the measured input before timing; KMC3 `-ci1 -cx<u32max> -cs<u32max>` |
| CI baselines | Regenerating from a dev host | Bootstrap only from the CI runner class's own artifacts (documented procedure in scripts/bench/README.md) |
| MSRV gate | Local stable clippy only | 1.80-aware clippy on both crates; MSRV-audit new deps |
| Error strings | Rewording pinned messages | `tests/007-api-compatibility/` asserts exact text; overflow message verbatim (`table.rs:296-301`) |
| `--size` / `initial_capacity` | Removing or honoring it literally in a partitioned engine | Keep parsing; document advisory semantics if the engine changes |

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Per-chunk producer barrier (`count.rs:481-506`) | CPU sawtooth; gz wall ≈ decompress + count | Bounded-queue producer/consumer overlap (P4) | Any input where decompression ≥ 20% of wall |
| Per-window O(k) encoding (`encode_kmer_bytes_u128`, `encoding.rs:221-252`) | Encode hot in flamegraph; cost scales with k | Rolling 2-bit encoder with mask + N-reset, differential-tested (P1 measures, P4 applies) | Every run; ~k base-ops per window vs O(1) rolling |
| `get_all_counts` full materialization (`table.rs:340-347`) | Output-time RSS ≈ 2× table; OOM at write | Stream sorted bucket runs to the writer; never collect the whole table into `Vec<(u128,u32)>` (24 B/entry second copy) | >100M distinct k-mers; fatal at human scale |
| Text-output sort decodes both keys to String per comparison (`count.rs:662-667`) | Text dump takes hours at scale | Sort by numeric key (same order for fixed k), decode once at write | >10M entries; catastrophic at 1B+ |
| Single-threaded gzip (D-02) | One core pegged during read phases | Pipeline overlap; file/member parallelism; rapidgzip-class only with audit | gz inputs always; ~100-200 MB/s/core ceiling |
| Tiny rayon tasks (per-record) | Stealing overhead dominates; scaling flat | Keep 4096-record chunks; granularity sweeps via harness | Task work < ~10 µs |
| Hundreds of open bucket writers | EMFILE on macOS (default 256) | Writer pool / capped open files; document ulimit (KMC precedent) | Bucket count > fd limit |
| Warm page cache in reps | 2× variance; "cold" claims false | Record true cache_state; counterbalanced reps; medians | Every repeated-input benchmark |

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Parsing bucket/temp files with unchecked indexing | Malformed spill file → panic → `panic="abort"` → no RAII cleanup (≈150 non-test `unwrap()` sites across parsers/merge already flagged in CONCERNS.md) | New spill readers use `?` + length validation; fuzz the bucket reader; TTL sweep is the backstop, not the plan |
| Predictable temp names | Symlink/collision attacks on shared tmp | Keep process-unique random subdirs (temp_lifecycle pattern) |
| `env::set_var` while rayon workers live | UB-adjacent std hazard (config/manager.rs:492-498, CONCERNS.md) | New code passes config explicitly; never mutate env after pool spawn |
| Adversarial low-complexity input | Bucket blowup → OOM/disk exhaustion DoS | Bucket admission + re-partition (Pitfall 3); disk guardrail (Pitfall 5) |
| Unbounded temp growth on repeated crashes | Disk exhaustion across runs | TTL sweep extended to counting prefix; sweep logs what it reclaimed |

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Silent spill: count suddenly 10× slower when budget exceeded | "rustkmer got slow" bug reports | Report the chosen mode + temp dir + estimated temp usage at start (merge already routes loudly) |
| Second `PyCounter(threads=N)` ignored | Python users think they control parallelism | Keep IN-04 warn; document build-once semantics in the docstring |
| Two-pass progress looks hung | Users kill pass 2 mid-run (orphan files) | Per-pass progress via indicatif (existing dep); document temp cleanup on interrupt |
| Temp disk surprise (hundreds of GB, KMC-class) | Filled disks on laptops | Pre-flight estimate + refusal with a clear message; document the disk/RAM tradeoff |
| Error-message drift | Pipeline scripts matching on text break | Contract-pinned strings stay verbatim |

## "Looks Done But Isn't" Checklist

- [ ] **Partitioned counting:** conservation + disjointness property tests pass on the edge matrix (len k-1/k/k+1/k+w-2/k+w-1, N positions, lowercase, palindromes, k ∈ {1,5,21,31,32,33,64}) — not just "tests green on the golden input"
- [ ] **Canonical minimizer:** `minimizer(x) == minimizer(revcomp(x))` proptest exists and runs in CI
- [ ] **Exact counts:** overflow boundary tests at u32::MAX-1/MAX per bucket AND across chunk sums; overflow message verbatim
- [ ] **Byte-identity:** golden sha256 vs pre-refactor output, sorted mode, both surfaces; sortedness proven through BOTH binary-search consumers
- [ ] **1-vs-N AND old-vs-new:** differential matrix across k × canonical, committed baselines (PCOUNT-04 extended)
- [ ] **CLI vs Python:** N-containing-read differential run and the semantics decision recorded (Pitfall 10) — surfaces actually agree
- [ ] **Python speed:** a Python-surface benchmark with a committed baseline shows the win (not just pytest correctness)
- [ ] **Multi-member gzip:** regression 8102985 green on every decoder path introduced
- [ ] **Temp lifecycle:** SIGKILL orphan → sweep test; ENOSPC injection test; sweep selector covers the counting prefix
- [ ] **Memory budget:** live RSS/phys_footprint red/green test at the declared cap (v1.0 bounded-memory harness shape); no mmap spill
- [ ] **Bucket skew:** histogram logged; adversarial poly-A input bounded; max/mean warning fires
- [ ] **KMC3 parity:** `-ci1 -cx<u32max> -cs<u32max>` config recorded; parity gate ran on the measured input BEFORE timing
- [ ] **MSRV:** 1.80 clippy green on both crates; new deps MSRV-audited
- [ ] **Baselines:** regenerated from the CI runner class, per platform; report states true cache_state
- [ ] **Binary provenance:** profile/bench artifacts carry binary sha256 + commit; Python module version asserted after rebuild

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Count-splitting / aliasing shipped (1, 2, 9) | HIGH | Databases produced are untrustworthy: recount from raw reads. Revert to the old path (keep it behind a flag until P5 proves the new one), fix, re-run the full differential matrix before re-enable |
| Byte-identity break (15) | MEDIUM | Revert the output stage; re-run goldens; if the change was intentional, surface the decision and regenerate fixtures with old-vs-new evidence attached |
| Orphan temp accumulation (5) | LOW | TTL sweep reclaims on next run; manual `rustkmer-count-*` removal per documented prefix; fix the selector pairing |
| Giant-bucket OOM (3) | MEDIUM | Re-partition fallback (MINIM-03) or raise budget; add the offending distribution to the adversarial test set |
| CI baseline breach (19) | MEDIUM | Re-bootstrap from CI artifacts per scripts/bench/README.md procedure — never from a dev host |
| Stale `.so` measured (13, 19) | LOW | `maturin develop --release`, verify module `__file__`/version, re-run; add the session-header assertion so it can't recur silently |
| KMC3 parity mismatch (18) | LOW | Methodology finding: fix the KMC3 flags, re-run parity, then timing; never touch rustkmer semantics to "match" |

## Pitfall-to-Phase Mapping

| # | Pitfall | Prevention Phase | Verification |
|---|---------|------------------|--------------|
| 1 | Canonical-unaware minimizer | P2 | proptest strand-invariance + old-vs-new differential (canonical on/off) |
| 2 | Bucket-local key leakage | P2 | round-trip property + release-mode conservation + golden sha256 |
| 3 | Giant buckets / skew | P2 design, P3 enforcement | bucket histogram on real slice + adversarial poly-A input bounded |
| 4 | Super-mer / read-end loss | P2 | conservation vs naive extractor on the edge matrix |
| 5 | Temp lifecycle / ENOSPC | P3 | SIGKILL sweep test, ENOSPC injection, prefix-selector pairing test |
| 6 | Disk I/O / fsync / fd limits | P3, P4 | iostat traces; macOS EMFILE test; no-fsync-on-temp review |
| 7 | mmap spill / dishonest admission | P3 | live max(rss, phys_footprint) red/green at the cap |
| 8 | Saturation / overflow drift | P2/P3, P5 proof | u32::MAX boundary tests + verbatim message + histogram review |
| 9 | Double-count across passes | P2, P5 | two conservation checks + 1-vs-N + old-vs-new matrix |
| 10 | Extraction-semantics drift (CLI/Python N divergence) | P1 decision, P2 shared core | CLI-vs-Python N-read differential; rolling-vs-per-window differential |
| 11 | Decompression masks gains | P1 measure, P4 fix | attribution table (gz vs plain); multi-member regression; parity gate |
| 12 | Rayon granularity / precedence | P2, P4 | --threads scaling runs; precedence unit tests stay green |
| 13 | GIL / PyO3 regressions | P5 + all verification | detach audit; thread-scaling pytest; rebuild+version assert |
| 14 | Hasher swap risks | P1 decide, P4 apply | profile evidence first; shard histogram; default-sort untouched |
| 15 | .rkdb byte-identity / sorted truth | P2 output, P5 proof | golden sha256 + both binary-search consumers |
| 16 | Dual-surface divergence | P1/P2 shared entry, P5 proof | Python benchmark with committed baseline shows the win |
| 17 | MSRV / dependency traps | All (P4 pressure) | 1.80 clippy both crates; dep MSRV audit |
| 18 | KMC3 benchmark unfairness | P5 | parity gate with exact-count KMC3 flags before timing |
| 19 | Stale binary / warm cache / bad slice | P1, P5 | binary fingerprint in artifacts; cache_state honesty; random slices |

## Sources

**Codebase (HIGH confidence — direct reading, 2026-11-11):**
- `src/hash/table.rs` (overflow Err semantics :265-301; narrow_to_dense T-03-09 :223-232; get_all_counts :340-347; IN-03 :460-473; overhead model :16-19)
- `src/cli/commands/count.rs` (CHUNK_SIZE/D-02 :21-30; per-chunk barrier :481-506; window semantics :377-411; header literal :725-736; default-sort D-09 :66-72; precedence :802-847)
- `pyo3/src/counter.rs` (sequential file loops + ACGT-strip :700-809; detach rationale :359-367; pool build-once/IN-04 :175-197)
- `src/hash/overflow.rs` (DiskOverflow: Drop closes only :149-153; sync_all :95; u64 keys)
- `src/database/temp_lifecycle.rs` (prefix :45; TTL :82; sweep :135), `src/database/streaming_merge.rs` (k-way merge)
- `src/kmer/canonical.rs:72-82`, `src/kmer/encoding.rs:221-252`, `src/io/fastq.rs:78` (MultiGzDecoder)
- `scripts/bench/bench.py` (parity gate :540-595; matched config :172-173; gzip incident :1291-1300), `scripts/bench/baselines/`
- `.planning/PROJECT.md`, `.planning/MILESTONES.md` (Known Gaps), `.planning/milestones/v1.0-REQUIREMENTS.md` (MINIM-01..03 :62-64), `.planning/codebase/CONCERNS.md` (note: pre-v1.0-close; its "counting single-threaded" claim is stale — current code is parallel)

**External (MEDIUM — cross-checked, ≥2 sources unless noted):**
- [KMC2/KMC3 benchmark study (GigaScience giy125 / PMC6280066)](https://pmc.ncbi.nlm.nih.gov/articles/PMC6280066/) — signatures, two-phase design, disk figures
- [IJC 2020 GPU super-k-mer counting](https://computingonline.net/files/journals/1/archieve/IJC_2020_19_4_01.pdf) — canonical minimizers §2.3
- [WABI 2022 (LIPIcs vol 242)](https://drops.dagstuhl.de/storage/00lipics/lipics-vol242-wabi2022/LIPIcs.WABI.2022.12/LIPIcs.WABI.2022.12.pdf) — temp-space limits, GIAB 350 GB
- [Discount: compact evenly distributed k-mer binning](https://www.biorxiv.org/content/biorxiv/early/2020/10/12/2020.10.12.335364.full.pdf) and [Gerbil/AdaOrder](https://www.biorxiv.org/content/10.1101/2021.12.02.470910v2.full.pdf) and [IIIT binning study](https://cdn.iiit.ac.in/cdn/rndshowcase.iiit.ac.in/tto2023/TTO_website_data/PDF/33.pdf) — bucket skew ratios
- [HKUST GPU counting thesis](https://repository.hkust.edu.hk/ir/bitstream/1783.1-167764/1/1783.1-167764.pdf) — MSP, super-mer boundaries, m vs bucket count
- [Syncmers (Edgar, PeerJ)](https://peerj.com/articles/10805/) and [Zheng minimizers review](https://kingsfordlab.cbd.cmu.edu/pdf/2023-zheng-minreview.pdf) — edge-window bias, segment overlap
- [pigz man page](https://man.freebsd.org/cgi/man.cgi?query=pigz&sektion=1&apropos=0&manpath=NetBSD+10.0) — decompression not parallelizable
- [Rapidgzip (arXiv 2308.08955)](https://arxiv.org/html/2308.08955v1) — speculative block finding, false positives, window reconstruction
- [Rust Performance Book — Hashing](https://nnethercote.github.io/perf-book/hashing.html) — fxhash/ahash/SipHash rustc measurements
- [hashbrown README benchmarks](https://raw.githubusercontent.com/rust-lang/hashbrown/0a62c3ec75ee3d3f039952d8ab218ee021d3a1e4/README.md) — hasher sensitivity on structured keys; [hashbrown bench suite](https://deepwiki.com/rust-lang/hashbrown/7-performance-and-benchmarks)
- [rustc-hash overview](https://deepwiki.com/rust-lang/rustc-hash/1-overview) — 2.x algorithm change, MSRV 1.77
- [KMC README](https://github.com/refresh-bio/KMC) — hundreds of temp files, ulimit -n 2048, 32 GB/389 GB figure
- [KMC source kmc_CLI/kmc.cpp usage text](https://raw.githubusercontent.com/refresh-bio/KMC/master/kmc_CLI/kmc.cpp) — -ci 2 / -cx 1e9 / -cs 255 / -m 12 / -sm off defaults; [KMC issue #136](https://github.com/refresh-bio/KMC/issues/136) — -cs 255 saturation cross-check
- [NUS CS4330 k-mer counting notes](https://www.comp.nus.edu.sg/~wongls/courses/cs4330/2024/08-kmers-counting-on-disk.pdf) — human-scale KMC3 RAM/disk figures
- [Bioinformatics btab797](https://academic.oup.com/bioinformatics/article-pdf/38/4/933/42319968/btab797.pdf) — I/O cost dominates disk-based counters

**External (LOW — single official-doc fetch; ctx7 CLI unavailable, context7 MCP not visible to this agent):**
- [rayon IndexedParallelIterator docs](https://docs.rs/rayon/latest/rayon/iter/trait.IndexedParallelIterator.html) — with_min_len/with_max_len hint semantics
- [PyO3 0.27 parallelism guide](https://pyo3.rs/v0.27.2/parallelism) — detach-around-spawn deadlock rule (corroborated by in-repo code comments, which raises practical confidence)

**Research cache:** 9 digests stored via `research-store` (keys from `research-plan`), 2026-11-11.

---
*Pitfalls research for: rustkmer v2.0 k=21 Counting Parity (minimizer/disk-backed/hasher additions to an exact-count system)*
*Researched: 2026-11-11*