# Architecture Research: v2.1 Integration — MERGE-BENCH & PEXT

**Domain:** Benchmark-harness extension (merge verdict) + producer-stage parallelization (count engine) on an existing shipped tool
**Researched:** 2026-11-16
**Confidence:** HIGH — every integration point below was read from the actual code this session (file:line anchors). No speculative redesigns; both tracks attach to structures that already exist and are pinned by tests.

---

## 1. Verified Integration Surfaces (as built today)

### 1.1 The count engine (PEXT target)

```
caller thread (THE producer)                       N persistent workers
─────────────────────────────────────              ─────────────────────────
open file  DefaultCompressedFileReader
           (engine.rs:806; gzip/bz2/xz)
bio FASTA/FASTQ record loop (engine.rs:820/835)
  └─ count_sequence (engine.rs:1001)
      └─ for_each_window (extract.rs:90)   ──┐
         rolling-encode k≤32 / per-window     │  per-key: partition_of
         u128 for k 33..=64                   │  (partition.rs:72, splitmix64)
  └─ route_key (engine.rs:1135)            ──┘
      per-partition RoutingBuffers            ┌─► sync_channel(8 batches) ─► run_worker
      (engine.rs:543)                         │   CountBatch::{Dense,Wide}    (engine.rs:1307)
  └─ send_batch (engine.rs:1189) when full ───┘   {partition, keys}           owns disjoint
                                                                              worker_range tables
file boundary → Flush{token} → 1 ack/worker                                    (owned_table :1386)
(engine.rs:1256 flush_pipeline, token :902)                                    LocalKmerCounts::increment
                                                                              (local.rs:152, u32 checked)
engine.finish() → join → concat tables in layout order → CountResult
count.rs: into_filtered_pairs → par_sort_unstable_by (sort_pairs_ascending, count.rs:364)
→ stream through frozen format.rs writer → .rkdb bytes identical for any thread count
```

Facts that constrain PEXT, verified from the code:

- **The producer does everything except increment.** Parsing, decompression, rolling encode, partition routing, and batch sends all run on the one caller thread (`count_file_inner`, engine.rs:803–871). Workers only drain queues and increment. Phase 7 measured this producer at ~99.99% of parallel wall — this is the PEXT target.
- **`for_each_window` is a pure, reentrant function** (extract.rs:90–148): fresh state per call, no cross-record state, sink-callback style. The natural parallel unit is the record (or a chunk of records).
- **Batches carry their partition tag** (`CountBatch::Dense/Wide { partition, keys }`, batch.rs:25–39) and worker-side `owned_table` (engine.rs:1386) re-validates ownership on every batch. Increments are per-key integer adds — **order-independent** within a partition. Consequently *who* produces a batch (and when) does not affect the final tables; only the file-boundary flush accounting is order-sensitive.
- **One worker has exactly one `sync_channel` and one ack channel** (engine.rs:711–712). The FIFO send→Flush→ack chain (batch.rs:10–17) is the happens-before edge behind `FileStats`; any multi-producer design must preserve or redefine it.
- **`--threads 1` is a true sequential path** (engine.rs:612–634) — no threads, no queues. It must stay untouched so the t1 baseline stays honest.
- **Thread composition is an exact, standing gate**: `expected_total` (tests/thread_pool_size_tests.rs:48–54) = 2 at N=1, **2N+1** for N>1 (1 main/producer + N engine workers + N rayon workers), observed by `.planning/research/profiling/verify_threads.py` in a subprocess. "The exactness is the point: no `>=`."
- **Profiling diagnostics exist and distinguish producer from workers**: `EngineDiagnostics { wall_nanos, producer_nanos, workers[] }` under `--features profiling` (engine.rs:196–204). The PEXT research phase can measure the producer share without new instrumentation; the predicted-win sizing derives from these numbers plus the extract/parse/decompress split.

### 1.2 The benchmark harness (MERGE-BENCH target)

`scripts/bench/bench.py` (2135 lines, stdlib-only, schema v1) already measures merge at slice scale:

- `build_merge_cmd` (bench.py:283) builds `rustkmer merge -i a.rkdb b.rkdb -o merged.rkdb`; the "merge" arm is appended to `arm_specs` whenever `--reps >= 2` and not `--skip-merge` (bench.py:1428–1432, 1460–1464).
- `run_comparison_protocol` (bench.py:1280) provides: one discarded warmup per **tool**, counterbalanced tool order per round (`round_schedule`, bench.py:1196 — keyed on tool name, so it generalizes to more arms unchanged), per-rep honest `cache_state` (`attempt_cache_purge`, bench.py:1220), cooldown gaps, medians + CV% (`reduce_arm`, bench.py:1239), post-run stats sanity (distinct == 0 aborts, bench.py:1339), and a pre-timing parity assertion between `count-A` and `jellyfish-count-A` (bench.py:1438–1449).
- Self-check already asserts **merge count conservation** (`merged total == sum of count totals`) and **distinct union** (`merged distinct >= max input distinct`) for every mode (bench.py:1479–1496).
- Measurement is `/usr/bin/time` wall + honest peak `max(rss, phys_footprint)` (`measure`/`parse_time_output`, bench.py:106–186); results carry full `binary_provenance` and `validate_schema`/`validate_provenance` gates; `check_disk_floor` (bench.py:1263) guards mode=full; `--merge-input` provisions the r1/r2 two-input arrangement (bench.py:529).
- The renderer already has merge-specific handling: `_arm_row` prints `n/a` deltas for the merge arm because "no jellyfish counterpart exists for the merge operation" (bench.py:1626–1629), and `_slice_section_lines` renders the conservation checks (bench.py:1745–1774).
- `scripts/bench/phase10.py` is the v2.0 full-scale verdict controller: staged (`synthetic → slice-gate → cli → python → render`), arms built by `build_arm_specs` (:210), rounds driven by `output_stage.rotation_schedule` (output_stage.py:121), exit-code contract 0/1/2 documented in its module docstring. It imports its primitives from bench.py. This is the established pattern for a multi-hour full-scale session.

The Rust merge side is a single shared entry: `rustkmer merge` → header-only compatibility validation (`merge.rs:392`) → `RKDatabase::merge_databases_to_path` (format.rs:1334) → `resolve_merge_route` admission control dispatches to streaming / prefix-cache / in-memory (format.rs:1341–1361). Rayon-parallel; the route is chosen by the header-only admission model, not by the user.

External fact (HIGH, official docs): `jellyfish merge -o out.jf in1.jf in2.jf` sums counts across inputs by default and is **single-threaded**, documented by the authors as "relatively slow"; jellyfish 2 users rarely need it because multi-threaded count self-merges. This asymmetry (no `-t` flag exists on merge) must be recorded in the report methodology like the existing decompression-pipe asymmetry note.

---

## 2. MERGE-BENCH: Integration Design

### 2.1 What the harness provides for free (nothing new needed)

| Capability | Where | Reuse for MERGE-BENCH |
|---|---|---|
| Counterbalanced reps, warmup-per-tool, cooldown | `run_comparison_protocol` (bench.py:1280) | Works unchanged for 6 arms — `round_schedule` rotates *tools*, arms of one tool run in spec order |
| Per-rep cache_state + round/arm_order recording | bench.py:1318–1321 | Free for every new arm |
| Honest peak memory `max(rss, footprint)` | `parse_time_output` (bench.py:106) | Both merge arms measured identically |
| Medians + CV% + cv_warning | `reduce_arm` (bench.py:1239) | Free |
| Zero-count sanity per arm | bench.py:1339–1344 | Catches an empty merged DB (Pitfall 1) |
| Input fingerprints, provenance, schema validation | bench.py:304–420, 1522–1536 | Free; SCHEMA_VERSION stays 1 (validate_schema tolerates new arm names) |
| Disk floor guard (mode=full) | `check_disk_floor` (bench.py:1263) | Reuse, but see pitfall §5.2 on the floor value |
| r1/r2 two-input provisioning | `--merge-input` (bench.py:529, 585) | Exactly the merge-bench input arrangement |
| Count-parity gate before timing | bench.py:1438–1449 | Keep; it underwrites the merge parity gates below |

### 2.2 New vs modified components

**New (bench.py):**

1. `jellyfish_merge_cmd(out, input_jfs)` — `["jellyfish", "merge", "-o", out, in1, in2]`, list-form, no shell (inputs are `.jf` files, never `.gz`; still `validate_path`-screen for consistency with T-04-03).
2. Arm specs added to the comparison matrix (bench.py:1420 block):
   - `{"name": "jellyfish-count-B", "tool": "jellyfish", "out": jf_b, "cmd": jellyfish_count_cmd(cfg_b, jf_b)}` — **new input**: today only `jf_a` exists (bench.py:1404); jellyfish merge needs a second `.jf`.
   - `{"name": "merge", ...}` — exists.
   - `{"name": "jellyfish-merge", "tool": "jellyfish", "out": jf_merged, "cmd": jellyfish_merge_cmd(jf_merged, [jf_a, jf_b])}`.
3. Merge parity gate in `run_bench` after the protocol (mirroring the existing count-parity block at bench.py:1438):
   - `merge.total == count-A.total + count-B.total` and `jellyfish-merge.total == same sum` (count conservation; overlapping k-mers contribute their **summed** counts — both tools sum by default, so the invariants coincide),
   - `merge.distinct == jellyfish-merge.distinct` (identical union semantics),
   - `merge.distinct >= max(input distinct)` (already in self-check; keep it there too).
4. **Deep slice-scale gate** (recommended): sorted multiset comparison of `rustkmer dump` vs `jellyfish dump` of the two merged databases — proves per-k-mer count equality including the summed overlap counts, not just the two aggregates. Full scale: stats-level gates only (dumping ~9 B records is prohibitive); state that honestly in the report.
5. Report renderer additions:
   - `_merge_arms(results)` helper + a `_merge_verdict` mirroring `_count_verdict` (bench.py:1653): verdict YES iff rustkmer-merge median wall ≤ jellyfish-merge median wall; the memory delta reported alongside (the MEM guardrail: peak RSS below jellyfish for any perf change).
   - Extend `_arm_row`'s merge special case: when a `jellyfish-merge` arm exists in the same results file, emit real deltas against it instead of hard-coded `n/a` (bench.py:1626–1629); fall back to `n/a` when absent so old results files still render byte-compatibly.
   - New report section "Merge verdict (invest/no-invest)" following the BENCH-02 verdict section's phrasing, plus a methodology line recording the jellyfish-merge single-threaded asymmetry (modeled on the decompression asymmetry note, bench.py:1823–1828).
6. Arm-ordering validation: assert in `run_comparison_protocol` (or a unit test in scripts/bench/tests/) that within each tool's spec order, count arms precede the merge arm — the round loop runs same-tool arms in spec order, so `count-A, count-B, merge` and `jellyfish-count-B, jellyfish-merge` orders make the per-round input dependencies hold. Today the rustkmer side relies on this ordering implicitly; make it explicit before adding the jellyfish side.

**Modified (bench.py):** `run_bench` arm_specs list; `main()` gains nothing mandatory — full-scale merge is already expressible as `--mode full --reps 3` without `--skip-merge`. Optionally a `--with-jellyfish-merge`/`--merge-only` convenience flag to trim session cost.

**Modified (scripts/bench/tests/):** unit tests for `jellyfish_merge_cmd` shape, the new parity-gate logic (GREEN/RED), renderer merge sections, and the ordering assertion. The 398-test harness suite is the regression net.

**New (optional, recommended): `scripts/bench/phase11.py`** — a thin staged controller modeled on phase10.py (synthetic tracer → slice-gate → full merge session → mechanical render, exit-code contract 0/1/2). Rationale: phase10.py exists precisely because a multi-hour full-scale session needs resumable stages and honest session-level provenance; bench.py remains the shared protocol library both controllers import. If the team prefers one file, bench.py alone can express the run — the staged controller is an ergonomics/provenance choice, not a capability gap.

**Rust side: zero changes.** The benchmark measures the shipped merge (admission-routed, `merge_databases_to_path`). Record which route `resolve_merge_route` picked per run as arm metadata (verbose stderr or a `--verbose` parse) so the verdict is attributed honestly ("streaming route, chunk = N records").

### 2.3 Verdict structure (what the report must answer)

Per PROJECT.md, MERGE-BENCH produces an **invest/no-invest** decision. The mechanical inputs:

1. Median wall + median peak RSS of `merge` vs `jellyfish-merge`, from recorded medians, counterbalanced reps, equality-is-match rule (same rule shape as `_count_verdict`).
2. Parity evidence lines proving both tools merged the same thing (conservation + union + slice-scale dump equality).
3. Methodology block: reps, schedule, cache states, `-s` hash size, the single-threaded-jellyfish asymmetry, fingerprints, provenance — all rendered with zero measurement literals per the T-04-07 contract.

---

## 3. PEXT: Integration Design

### 3.1 Where parallel extraction attaches

The attach surface is small and precisely bounded: **everything between `DefaultCompressedFileReader::open_compressed` (engine.rs:806) and the routing buffers (engine.rs:1135)** runs on the producer thread. Two viable designs:

### Design A — per-chunk extraction tasks on the existing rayon pool (RECOMMENDED)

```
producer thread (dispatcher)                        rayon pool (N threads)          N workers (unchanged)
──────────────────────────────                      ─────────────────────           ─────────────────────
read records → raw chunk (≤C records)
spawn extraction task (bounded in-flight W)
                                     ─────────────► parse + for_each_window
                                                    → per-partition key buffers
                                     ◄─────────────  returned Vec per partition
drain completed chunks (any order)
  route_key / send_batch  ──────────────────────────────────────────────────────► UNCHANGED queues,
(unchanged code path, engine.rs:1135/1189)                                        Flush{token} protocol,
file boundary: joint flush as today                                              acks, 2N+1 threads
```

- **New:** a chunk-reader on the producer thread + an extraction closure (records → `RoutingBuffers`-shaped partial buffers); `EngineConfig` grows bounded-in-flight knobs (e.g. `extraction_chunk_records`, `max_in_flight_chunks`). Returns are routed by the **same** `route_key`/`send_batch` code, so `send_batch` remains the *only* sender into each worker queue.
- **Unmodified:** `CountBatch`/`WorkerStat`, `flush_pipeline` + token/ack protocol, `run_worker`, `owned_table`, `PartitionLayout`, the sequential path, `Drop`, `finish`, and the entire output stage. `count.rs` and `pyo3/` see no API change.
- **Why the shape is deadlock-safe:** rayon tasks must never block on a worker queue (the module docs already warn the inverse case: engine.rs:20–22). Here tasks only *return* buffers; the dispatcher is the sole sender and applies backpressure by bounding in-flight chunks — a full queue blocks the dispatcher, which stops issuing new chunks; memory is bounded by W × chunk size. This preserves the bounded-memory property the pipeline was designed around.
- **Thread observability:** extraction tasks run on the global rayon pool sized `resolved_threads` (count.rs:152–155) → process total stays exactly **2N+1**; `thread_pool_size_tests.rs` and `verify_threads.py` pass unchanged.

### Design B — M producer OS threads feeding the same worker queues

- Mechanically possible without touching workers: `SyncSender` is `Clone`, so M producers can hold senders into each worker's single-receiver channel; per-key adds commute, so interleaved batches count identically.
- **But the flush protocol breaks:** a producer's Flush ack proves only *its own* batches were consumed (the ack answers one FIFO channel; with M senders interleaved, "everything sent so far by all producers" is not established by one ack). File-boundary cumulative `FileStats.stats` — a published, tested contract — becomes ill-defined mid-flight. A correct design needs M flush tokens per barrier and a joint reduction (worker counts outstanding producers, or an M-way ack rendezvous), i.e. a rewrite of `flush_pipeline`/`WorkerStat` plus new shutdown/Drop ordering across producer threads.
- **Costs beyond the engine:** the 2N+1 exactness gate becomes 2N+M+1 → `expected_total` (thread_pool_size_tests.rs:48) and `verify_threads.py` must change; profiling diagnostics need per-producer splits; file-ownership vs chunk-splitting of one file changes skip-warning batch semantics (the per-4096-record legacy wording, engine.rs:1405–1444).
- **Verdict:** strictly more surface for the same win. Design A already parallelizes the measured bottleneck (encode/parse/decompress — the routing and send costs are tiny per key) while inheriting every pinned invariant. Choose B only if Design A measurements show the dispatcher's route+send hop is itself significant (measurable via the existing `profiling` feature before committing).

### 3.2 Invariants PEXT must preserve (each one a success criterion)

| # | Invariant | Existing enforcement | PEXT success criterion |
|---|---|---|---|
| 1 | **Disjoint partition writes** — every key hits exactly one table | `partition_of` purity (partition.rs:72), `owned_table` range check (engine.rs:1386) | Routing logic unchanged or provably identical; `owned_table` validation still fires on any out-of-range batch (keep a RED-testable mutation) |
| 2 | **Exact counts, verbatim overflow** | `LocalKmerCounts::increment` u32 checked (local.rs:152); checked aggregate sites (engine.rs:108–171) | 1-vs-N and old-vs-new differentials byte-exact across the k/canonical matrix; seeded-overflow test (engine.rs:1577) still returns the verbatim message without hanging |
| 3 | **`.rkdb` byte-identity across thread counts** | partition-disjointness + strict total-order sort (count.rs:364) + frozen writer | t1/t4/t16 sha256 equality gate re-run and green on the new engine |
| 4 | **2N+1 thread observability (Design A)** | `expected_total` (thread_pool_size_tests.rs:48), `verify_threads.py` | Gate passes unchanged; no new named OS threads from extraction |
| 5 | **Flush/token happens-before** | FIFO channel + token echo (batch.rs:10–17, engine.rs:1256–1299) | `flush_pipeline` untouched; stale-token test still RED-controllable |
| 6 | **t1 honesty** | sequential path (engine.rs:612–634) | `--threads 1` path byte-for-byte untouched; t1 wall statistically unchanged (it shares no new code) |
| 7 | **Bounded memory** | bounded queues (8 batches), `into_filtered_pairs` drain-don't-copy, MEM guardrail | In-flight chunk bound W documented and enforced; full-scale peak RSS stays **below jellyfish at both k** (43.97 GiB k=21 / 68.52 GiB k=31 references) |
| 8 | **Frozen Python surface (12 public `PyCounter` methods)** | Phase 9 freeze (pyo3/src/counter.rs:117–655) | Zero API changes; `count_file_into_counter` (pyo3/src/counter.rs:676) benefits transparently because it constructs a per-call `CountEngine`; 179 pytest green with no new expectations |
| 9 | **Engine contracts in prose stay true** | module docs (engine.rs:1–53): workers never print/rayon/unwrap | Extraction tasks inherit the same rules (no unwrap, errors fail loud through the established paths) |
| 10 | **Error/shutdown: no leaked or blocked worker** | `join_workers` idempotent, `Drop` joins (engine.rs:1056–1129) | A failed extraction join-fails loud; Drop still terminates everything under any chunk stage state |

### 3.3 PEXT research-phase leverage (this milestone)

The predicted-win sizing needs no new instrumentation: build with `--features profiling`, run the real slice, and read `EngineDiagnostics.producer_nanos` vs worker `busy_nanos` (engine.rs:196–204) — the same diagnostics that produced the "producer ≈99.99%" finding. Decompress/parse/encode attribution may want one targeted sub-timing inside the producer (a research-phase-local patch or a `profiling`-gated counter), kept out of default builds per the existing pattern. The conditional implementation phase then re-uses the bench harness's rotation/median machinery (output_stage.rotation_schedule, reduce_arm) for its scaling gate, exactly as Phases 6–8 did.

---

## 4. Data Flow Changes

**MERGE-BENCH:** none in Rust. In the harness, the results document gains arms (`jellyfish-count-B`, `jellyfish-merge`), the parity block gains merge-level assertions, and the rendered report gains a merge-verdict section. Flow of measured bytes: `inputs → {rk count A,B; jf count A,B} → {rk merge; jf merge} → stats/dump parity → medians → verdict`.

**PEXT (Design A):** the record→keys flow gains one stage boundary. Producer thread: read raw chunk → rayon task: decompress/parse/encode → returned per-partition buffers → producer routes/sends (unchanged) → workers increment (unchanged) → finish/sort/write (unchanged). Aggregates (skipped windows, warning batches) remain producer-side and exact because the dispatcher sees every chunk's summary in one thread — a deliberate Design A advantage over Design B, where skip accounting would scatter across producers.

---

## 5. Build Order (dependency-aware)

**Recommended sequence — MERGE-BENCH harness first, PEXT research parallel, PEXT implementation last and conditional:**

1. **Harness extension (MERGE-BENCH spine; also serves PEXT later).** Add the jellyfish-count-B/merge arms, merge parity gates, dump-level slice gate, ordering assertion, renderer verdict section, unit tests. Small, fully testable at synthetic scale in CI (`benchmark.yml` runs bench.py synthetics already). *No Rust changes → all subsequent measurements share one harness.*
2. **PEXT research (independent of 1; can run in parallel).** Profiling builds, producer-share measurement, predicted-win sizing on the real slice, Design A vs B decision memo. Reads the engine only; changes nothing, so step 3's measurements stay attributable to a stable binary.
3. **Full-scale merge session → invest/no-invest verdict** (user decision point; phase11-style controller optional). Must complete *before* any PEXT implementation lands: a merged binary would change provenance and force re-running the merge session (new binary hash → new provenance block → previous full-scale numbers no longer renderable as final).
4. **PEXT implementation phase — conditional (D3 pattern).** Executes only if step 2's verdict says the predicted win justifies it. Reuses step 1's harness for its scaling and parity gates (same rotation schedule, same reduce/verdict rules, `.rkdb` sha256 gates). If triggered, its own old-vs-new differential runs *after* the merge verdict is recorded, on a fresh provenance.

**Why this order holds:** the only hard dependency is 2→4 (research gates implementation) and 3-before-4 (provenance stability). Steps 1 and 2 are mutually independent; doing 1 first is cheap insurance because PEXT's implementation phase (if triggered) is the second consumer of the extended harness, and every harness bug is then found at synthetic scale, not mid-session.

---

## 6. Anti-Patterns to Avoid (domain-specific)

1. **Do not let rayon tasks send into worker queues.** Bounded queues + a blocked pool = deadlock (the module docs' warning inverted). Design A's dispatcher-only-send rule is the guard.
2. **Do not weaken the exactness gates to "counts still equal at the end."** The byte-identity and 2N+1 gates are exact-equality by design ("the exactness is the point"); a `>=` relaxation is how the v1.0 `--threads` no-op survived a year.
3. **Do not compare merge wall against a jellyfish *count* arm.** The current renderer's `n/a` for merge exists precisely because that delta is semantically void (bench.py:1626); MERGE-BENCH must add the true counterpart arm, not reuse the count baseline.
4. **Do not let the merge benchmark re-run `jellyfish merge` on self-merged inputs.** jellyfish count with `-t > 1` already merges internally; the two `.jf` inputs must come from two separate single-database count runs (the harness's per-input arm structure gives this naturally — preserve it).
5. **Do not "fix" the single-threaded jellyfish merge asymmetry by throttling rustkmer.** Record it in the methodology section (the decompression-asymmetry precedent) and compare shipped defaults.
6. **Do not add PEXT knobs to the Python surface.** Engine config is Rust-side; `PyCounter`'s 12-name API is frozen and `threads=` already covers configuration.

---

## 7. Pitfalls Worth a Phase-Level Flag

| Topic | Pitfall | Mitigation |
|---|---|---|
| Full-scale merge disk usage | DEFAULT_DISK_FLOOR_GB = 150 was sized for count artifacts (bench.py:61–63); a full merge session adds 2×.jf + 2×.rkdb merged outputs + scratch | Re-estimate from v2.0 measured DB sizes; raise `--disk-floor-gb` for the merge session |
| jellyfish counter saturation at merge | Summed counts can exceed what count-time parity exercised | The stats-level parity gates catch any divergence; note `--out-counter-len` if ever needed (default worked at v2.0 scale) |
| Renderer regression risk | `_arm_row`'s merge special-case is load-bearing for old committed results files | New code path only when `jellyfish-merge` arm present; byte-identity re-render check on the v2.0 committed JSONs |
| Admission-route attribution | Full-scale merge route (streaming vs prefix-cache) is chosen by the admission model, not visible in results | Record `resolve_merge_route`'s decision as arm metadata; verdict wording names the measured route |
| In-flight memory bound (PEXT) | Unbounded chunk queue reintroduces v1.0-style RSS blowups | W × chunk bound is a documented EngineConfig invariant with a test |

---

## 8. Sources

- Codebase (this session, HIGH): `src/count/engine.rs` (engine pipeline, producer loop, flush protocol, diagnostics), `src/count/partition.rs` (routing/layout), `src/count/batch.rs` (message contracts), `src/kmer/extract.rs` (`for_each_window` purity), `src/cli/commands/count.rs` (pool init, sort, frozen writer flow), `src/cli/commands/merge.rs` (CLI merge, header-only validation), `src/database/format.rs` (`merge_databases_to_path` + route dispatch), `src/hash/local.rs` (increment/overflow), `pyo3/src/counter.rs` (per-call engine, frozen API), `tests/thread_pool_size_tests.rs` (2N+1 gate), `scripts/bench/bench.py` (protocol, parity, self-check, renderer), `scripts/bench/phase10.py` + `scripts/bench/output_stage.py` (staged full-scale pattern, rotation schedule), `scripts/bench/compare.py` (threshold contract), `.github/workflows/benchmark.yml` (CI gate), `.planning/PROJECT.md` (milestone scope, D3 pattern, MEM guardrail).
- Web (HIGH, official documentation): Jellyfish 2.3 `merge` subcommand — syntax `jellyfish merge [options] hash1 hash2 ...`, `-o` output, count-summing default, single-threaded and documented "relatively slow":
  - [Debian jellyfish(1) man page](https://manpages.debian.org/trixie/jellyfish/jellyfish.1.en.html)
  - [Jellyfish 2.3.0 manual (PDF)](https://gensoft.pasteur.fr/docs/jellyfish/2.3.0/jellyfish.pdf)
  - [Jellyfish User Guide](http://home.cc.umanitoba.ca/~psgendb/birchhomedir/BIRCHDEV/public_html/doc/jellyfish/JellyfishUserGuide.pdf)

---
*Architecture research for: rustkmer v2.1 — MERGE-BENCH harness extension & PEXT producer integration*
*Researched: 2026-11-16*
