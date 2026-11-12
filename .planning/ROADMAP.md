# Roadmap: rustkmer

## Milestones

- ✅ **v1.0 Performance** — Phases 1-4 (shipped 2026-10-20)
- 🚧 **v2.0 k=21 Counting Parity** — Phases 5-11 (in progress; Phase 11 conditional on D3)

## Phases

<details>
<summary>✅ v1.0 Performance (Phases 1-4) — SHIPPED 2026-10-20</summary>

- [x] Phase 1: Foundation & Quality (4/4 plans) — completed 2026-07-01
- [x] Phase 2: Parallel Counting (5/5 plans) — completed 2026-07-01
- [x] Phase 3: Memory Safety (17/17 plans) — completed 2026-10-09
- [x] Phase 4: Benchmark & Validation (5/5 plans) — completed 2026-10-18

Full detail: [milestones/v1.0-ROADMAP.md](milestones/v1.0-ROADMAP.md) · Summary: [MILESTONES.md](MILESTONES.md)

</details>

### 🚧 v2.0 k=21 Counting Parity (Phases 5-11)

**Milestone Goal:** Match or beat Jellyfish2 on human-scale k=21 counting (and k=31 under fair, matched-hash comparison) on BOTH the CLI and Python surfaces, closing the BENCH-02 gap outright. Approach ratified from empirical profiling (D1): the ~5x gap is ~3.5x parallel-scaling inefficiency × ~1.4x single-thread cost — not a data-structure problem. Stage A in-memory parallelism (Phases 5-10) is the spine; Stage B minimizer/disk-backed (Phase 11) is conditional on D3.

- [ ] **Phase 5: Measurement & Regression Harness** - Standing slice bench + parity gate, --threads reality tests, contention microbench, Python baseline, N-read differential
- [ ] **Phase 6: Parallelism Correctness & Hot Path** - Working --threads, thread-local counters with end reduction (no per-window atomics), rolling encode + bit-parallel revcomp
- [ ] **Phase 7: Shared Counting Engine** - One src/count/engine.rs entry point: persistent workers, disjoint partitioned tables, overlapped producer/consumer (the ~3.5x lever)
- [ ] **Phase 8: Output Pipeline & .rkdb v2 Parity** - Unstable/parallel sort + streaming write; golden byte-identity, both-consumer sortedness, full differential matrix
- [ ] **Phase 9: Python Parity** - PyCounter routed through the shared engine, D2 skip-N semantics documented, measured win vs the Phase 5 baseline
- [ ] **Phase 10: Benchmark Verdict** - Full human-scale jellyfish parity verdict on both surfaces + KMC3 exact-count comparison (BENCH-V2-01)
- [ ] **Phase 11: Minimizer Partitioning & Memory Ceiling** - CONDITIONAL (D3): hand-rolled canonical minimizers + skew-controlled disk-backed bins — only if Stage A misses parity or a memory ceiling Stage A cannot meet

## Phase Details

**Phase numbering:** continues from v1.0 (Phases 1-4 shipped, archived under `milestones/v1.0-phases/`). Integer phases are planned milestone work; decimal phases (e.g. 6.1) are urgent insertions created via `/gsd-phase --insert`.

**Execution order:** 5 → 6 → 7 → 8 → 9 → 10 → (11 only if D3 triggers). Flex points from research: Phases 6 and 7 may merge if planning finds thread-local counters inseparable from the engine; Phases 8 and 9 may partially overlap. Never run Phase 10 before Phases 8 and 9 — the verdict requires both surfaces proven.

**Guardrails (bind every phase's success criteria):**
- Exact u32 counts; fail-loud overflow at `u32::MAX` with the verbatim contract-pinned message; checked arithmetic in every new summation — never saturating/wrapping.
- `.rkdb` v2 byte-identity (sorted mode); single `format.rs` writer; frozen header literals (IN-03 total_kmers meanings preserved); public CLI/Python APIs unchanged — any break is a surfaced user decision only.
- MSRV 1.82 / Python ≥3.11: the 1.82 toolchain must be installed and MSRV-aware clippy run on BOTH crates; audit new deps for edition-2024/MSRV/global-allocator traps.
- PyO3: `py.detach` + owned Send captures around all parallel/blocking work; no global allocator reachable from the core rlib/cdylib; rebuild (`maturin develop --release`) + module version-assert before every pytest.
- Benchmark honesty: parity before timing; true per-rep cache_state; medians of counterbalanced reps; CI baselines only from the CI runner class; binary/module provenance (sha256 + commit + build profile) on every artifact.

### Phase 5: Measurement & Regression Harness
**Goal**: Every downstream performance claim is measured against standing, reproducible gates — parity checked before timing, provenance on every artifact — and the known measurement gaps (thread reality, contention attribution, Python baseline, N-read divergence) are closed with recorded evidence.
**Depends on**: Nothing (first v2.0 phase; builds on shipped v1.0 Phases 1-4 harness infrastructure)
**Requirements**: PROF-01, PROF-02, PROF-03, PROF-04, PROF-05
**Success Criteria** (what must be TRUE):
  1. A reproducible slice benchmark runs on the measured CRR1936095 input and gates on pinned count parity (Distinct 229,694,874 / Total 519,271,168 vs jellyfish); every result artifact records binary provenance (sha256 + commit + build profile); subslices are random-record, not head-of-file.
  2. A `--threads` correctness test asserts the ACTUAL rayon pool size and is observably RED on the current tree (17 OS threads at `--threads 1`); a thread-scaling gate records t1/t4/t16 wall-clock and is RED while the flag is a no-op — the standing gates Phase 6 must turn green.
  3. A multi-thread contention microbench produces a recorded split of the ~9.4x in-vivo increment multiplier into global-atomics vs memory-bandwidth shares, persisted as evidence that tunes Phase 7's engine design.
  4. A Python-surface counting benchmark runs and its sequential-pipeline baseline is committed, so Phase 9 can prove a win by measurement rather than assertion.
  5. A CLI-vs-Python N-read differential is executed and recorded, quantifying the chimeric-k-mer divergence that the D2 skip-N unification resolves.
**Plans**: 7/7 plans executed
Plans:
- [x] 05-01-PLAN.md — Provenance builder + thread-scaling gate (tracer; expected RED on current tree)
- [x] 05-02-PLAN.md — Rust 1.80 MSRV toolchain + CI clippy pins + random-record slicer
- [x] 05-03-PLAN.md — Pool-size reality tests + RED evidence + pre-refactor golden capture
- [x] 05-04-PLAN.md — Slice parity gate + real-data baselines (pinned parity, RED scaling baseline)
- [x] 05-05-PLAN.md — Contention microbench + atomics-vs-bandwidth evidence (Phase 7 input)
- [x] 05-06-PLAN.md — Python counting baseline + N-read differential (D2 evidence)
- [x] 05-07-PLAN.md — Standing CI gates + README procedures / Phase 6 handoff
**Research flag**: none — standard patterns; the harness and profiling scripts already exist (`scripts/bench/`, `.planning/research/profiling/`); this is extension, not discovery.
**Note**: Install the Rust 1.82 toolchain here so MSRV-aware clippy on both crates gates every later phase. Capture pre-refactor golden `.rkdb` sha256 baselines here (consumed by OUT-02 in Phase 8) — goldens must exist BEFORE any Phase 6/7 hot-path change lands; never regenerate them to make a diff green.

### Phase 6: Parallelism Correctness & Hot Path
**Goal**: Thread control actually works and the single-thread hot path is measurably faster while counts stay exactly equal — establishing the true t1 baseline and contention-free accumulation before the engine restructure.
**Depends on**: Phase 5 (pool-size + scaling gates exist to prove the fix; goldens captured)
**Requirements**: PAR-01, PAR-02, PAR-03
**Success Criteria** (what must be TRUE):
  1. `--threads N` sizes the actual rayon pool (Phase 5's pool-size test green; `--threads 1` runs one worker), with the `--threads > RUSTKMER_THREADS > RAYON_NUM_THREADS > num_cpus` precedence chain and Python `threads=` / IN-04 warn semantics preserved (lazy fallback via `available_parallelism`; `build_global` before any rayon query).
  2. Counting accumulates in thread-local counters reduced at end-of-run — per-window `total_kmers`/`unique_kmers` fetch_add is gone from the hot path — and the reduction uses checked arithmetic that fails loud with the verbatim u32 overflow error (a new overflow site, never saturating); the thread-scaling gate shows wall-clock differing across t1/t4/t16.
  3. The rolling 2-bit encoder + bit-parallel reverse-complement (u64 for k≤32) passes the differential edge matrix against the per-window encoder — N at every position, lowercase, record boundaries, k ∈ {1..64} — masking to 2k bits and resetting the valid run at every N and record boundary; the u128 path remains for k>32 and API stability.
  4. A true single-thread baseline is recorded on the slice via the now-working `--threads 1`, single-thread slice time improves measurably (the microbench-measured 2.7x rolling-encode lever), and all existing golden baselines + 1-vs-N differentials stay green — exact counts and `.rkdb` v2 byte-identity preserved.
**Plans**: TBD
**Research flag**: none — the bug mechanism is confirmed in rayon-core source; the rolling encoder is already implemented and key-verified in the profiling microbench.

### Phase 7: Shared Counting Engine
**Goal**: CLI counting runs through one shared engine — persistent workers, disjoint partitioned tables, overlapped producer/consumer I/O — recovering the measured ~3.5x parallel-scaling deficit, with Python inheritance structural rather than accidental.
**Depends on**: Phase 6 (thread-local counters + rolling encode are prerequisites; PROF-03 contention evidence tunes the design)
**Requirements**: ENGINE-01, ENGINE-02, ENGINE-03
**Success Criteria** (what must be TRUE):
  1. ONE counting entry point (`src/count/engine.rs`) exists and CLI counting runs through it: a fixed rayon pool built before any rayon query, a producer streaming records into a bounded queue, and N persistent workers counting into disjoint hash-range-partitioned thread-local tables with overlapped decompression — the per-chunk fork-join barrier is gone.
  2. The PROF-02 thread-scaling gate is green after the engine: parallel-scaling efficiency materially improves toward jellyfish's measured 8.9x-on-16-cores profile and slice wall-clock drops measurably vs the Phase 6 baseline, recorded with parity-before-timing and provenance on every artifact.
  3. ONE core window-extraction function implements the D2 skip-N semantics (CLI output stays identical to the jellyfish-validated reference), and the MultiGzDecoder multi-member gzip regression (v1.0 8102985) stays green.
  4. Exact counts survive partitioning: the slice parity gate passes on the pinned Distinct/Total, disjointness + conservation property tests are green, and every new summation site fails loud with the verbatim u32 overflow message.
**Plans**: TBD
**Research flag**: `--research-phase` recommended — partition scheme (hash-range vs canonical-minimizer) for the in-memory tables, queue/batch sizing on P+E hybrid cores, atomics-vs-bandwidth isolation (consume the PROF-03 microbench evidence first). Highest-leverage phase; design evidence pays for itself.
**Note**: ENGINE-01/ENGINE-03's dual-surface contract completes in Phase 9, where `PyCounter::add_from_*` routes through this engine and the D2 semantics is proven + documented on the Python side (PY-01/PY-02). Phase 7 builds the engine as the single entry point and wires the CLI.

### Phase 8: Output Pipeline & .rkdb v2 Parity
**Goal**: Counting output is fast (unstable/parallel sort, streaming write) and byte-level compatibility of every new counting path is proven — the milestone's contract gate before any verdict runs.
**Depends on**: Phase 7 (the engine's sorted stream feeds the output stage)
**Requirements**: OUT-01, OUT-02, OUT-03
**Success Criteria** (what must be TRUE):
  1. Output uses unstable/parallel sort (`sort_unstable_by_key` / `rayon::par_sort_unstable`) and streaming write with no `get_all_counts` full materialization; text output sorts by numeric key; the output phase's slice wall-clock drops measurably (from the measured ~13.4 s single-thread stable sort on 229M keys).
  2. `.rkdb` v2 byte-identity is proven: golden sha256 captured BEFORE the refactor (Phase 5) match post-refactor output; sortedness is proven through BOTH binary-search consumers (`DatabaseQuery` AND prefix query); header literals and the single `format.rs` writer stay frozen (IN-03 total_kmers meanings preserved).
  3. An old-vs-new AND 1-vs-N differential matrix across k × canonical passes for every new path (partitioned tables + end reduction), with disjointness and conservation property tests green.
  4. The proof gates demonstrably fail on injected defects (overflow / duplication / ordering mutations observed RED) — goldens are never regenerated to make a diff green, and overflow at every new site returns the verbatim fail-loud error.
**Plans**: TBD
**Research flag**: none — sort + existing writer + existing golden/differential discipline (v1.0 DENSE-02 / PCOUNT-04 precedents).

### Phase 9: Python Parity
**Goal**: Python users get the same engine speed and counting semantics as the CLI — proven by measurement against the Phase 5 baseline — with the public API frozen and the N-read output change explicitly documented.
**Depends on**: Phase 7 (shared engine), Phase 8 (output parity proof); may partially overlap Phase 8 during planning
**Requirements**: PY-01, PY-02
**Success Criteria** (what must be TRUE):
  1. `PyCounter.add_from_fastq` / `add_from_fasta` count through the shared engine (no longer a sequential line loop), the public `PyCounter` API is unchanged, and the `save_database` double-sort is gone.
  2. Every parallel/blocking PyO3 path uses `py.detach` with owned Send captures (no GIL deadlock under concurrent use); the extension is rebuilt (`maturin develop --release`) and version-asserted before every pytest run (stale `.so` shadowing is a known trap).
  3. Python output on N-containing reads matches the CLI skip-N semantics (D2): the PROF-05 differential re-run shows the chimeric-k-mer divergence eliminated, and the user-visible output change is documented — never silent (WR-04 precedent).
  4. The Python benchmark shows a measured wall-clock win against the committed Phase 5 sequential baseline, recorded with parity-before-timing and module provenance.
**Plans**: TBD
**Research flag**: none — the v1.0 shared-entry merge precedent (`merge_databases_to_path`) is the template; PyO3 detach patterns are in-repo.

### Phase 10: Benchmark Verdict
**Goal**: The milestone's acceptance question is answered with honest, reproducible measurement at full human scale on both surfaces — the jellyfish parity verdict plus the KMC3 exact-count comparison as second reference.
**Depends on**: Phase 8 AND Phase 9 (both surfaces proven correct before any verdict; never run this phase before them)
**Requirements**: BENCH-V2-01, BENCH-V2-02
**Success Criteria** (what must be TRUE):
  1. A KMC3 3.2.4 comparison runs with exact-count configuration (`-ci1 -cx4294967295 -cs4294967295`, matched threads/canonical, agreed `-m`; official mac.arm64 tarball, `ulimit -n 2048`); count parity on the measured input passes BEFORE any timing; temp-disk usage is recorded; the harness degrades gracefully when KMC3 is absent.
  2. A full human-scale jellyfish parity verdict is produced on BOTH surfaces — slice gate green at every step before the full run — from medians of counterbalanced reps with honest per-rep cache_state, the verdict computed from the recorded medians.
  3. The acceptance question is answered by measurement: rustkmer matches or beats jellyfish at k=21 (and k=31 under fair, matched-hash comparison). A YES closes BENCH-02 outright; a NO is recorded honestly and feeds the D3 trigger decision for Phase 11.
  4. CI baselines are regenerated only from the CI runner class; every verdict artifact carries binary/module provenance; the report states cold-cache limitations honestly (no-sudo warm-cache reality recorded, as in v1.0).
**Plans**: TBD
**Research flag**: `--research-phase` recommended — re-verify KMC3 exact-flag behavior at run time against the pinned 3.2.4 release (source checked was master); install + `ulimit` + temp-disk accounting on macOS.

### Phase 11: Minimizer Partitioning & Memory Ceiling
**Goal**: (If triggered) counting peak RAM is bounded to the largest bucket via hand-rolled canonical minimizer partitioning with disk-backed bins — the memory-ceiling / KMC3-RAM lever — while exact counts and `.rkdb` v2 byte-identity survive.
**Depends on**: Phase 10 (verdict + memory measurements provide the trigger evidence); reuses Phase 7's partitioned engine + v1.0 external-sort/temp-lifecycle machinery
**Conditional**: D3 (user-ratified 2026-11-12) — executes ONLY if Stage A misses the parity gate OR the user sets a memory ceiling Stage A cannot meet (e.g. beating KMC3 on RAM). If Stage A hits parity and memory is acceptable, MINIM-01..03 descope/defer to a later milestone. No new persistence engine; MSRV-clean hand-roll (no edition-2024 minimizer crates).
**Requirements**: MINIM-01, MINIM-02, MINIM-03 (conditional)
**Success Criteria** (what must be TRUE):
  1. Hand-rolled canonical minimizer/signature extraction (KMC2 exclusion rules: AAA*/ACA*/internal AA) + super-mer runs passes a strand-invariance proptest (canonical minimizer = min(m-mer, revcomp(m-mer)), tie-breaks matching `canonical_kmer_u128`), MSRV 1.82-clean.
  2. Bins are skew-controlled: an adversarial poly-A input produces a bounded max/mean bucket ratio via adaptive re-partition (bucket histogram recorded); `--max-memory` counting admission accounts bytes honestly; the temp lifecycle uses a counting prefix paired with the prefix-based TTL sweep selector (`DiskOverflow` not reused).
  3. Disk-backed bucket spill reads via BufReader (never mmap under an RSS budget), and a bounded-RAM proof is measured as a max(rss, phys_footprint) red/green gate; the KMC3 memory comparison is recorded.
  4. Exact counts and `.rkdb` v2 byte-identity survive the disk-backed path: the differential matrix, golden sha256, and both-consumer sortedness proofs stay green; overflow fails loud with the verbatim message.
**Plans**: TBD (only if D3 triggers)
**Research flag**: `--research-phase` required if triggered — KMC3 primary-paper details (signature→bin packing, RADULS-class sort), bucket-skew measurement on the real slice, MSRV-clean hand-roll design. Sparse primary sources; the primary KMC3 paper was not directly retrieved during milestone research.

## Progress

**Execution Order:**
Phases execute in numeric order: 5 → 6 → 7 → 8 → 9 → 10 → (11 only if D3 triggers). Decimal insertions execute between their surrounding integers.

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Foundation & Quality | v1.0 | 4/4 | Complete | 2026-07-01 |
| 2. Parallel Counting | v1.0 | 5/5 | Complete | 2026-07-01 |
| 3. Memory Safety | v1.0 | 17/17 | Complete | 2026-10-09 |
| 4. Benchmark & Validation | v1.0 | 5/5 | Complete | 2026-10-18 |
| 5. Measurement & Regression Harness | v2.0 | 7/7 | In Progress | - |
| 6. Parallelism Correctness & Hot Path | v2.0 | 0/TBD | Not started | - |
| 7. Shared Counting Engine | v2.0 | 0/TBD | Not started | - |
| 8. Output Pipeline & .rkdb v2 Parity | v2.0 | 0/TBD | Not started | - |
| 9. Python Parity | v2.0 | 0/TBD | Not started | - |
| 10. Benchmark Verdict | v2.0 | 0/TBD | Not started | - |
| 11. Minimizer Partitioning & Memory Ceiling | v2.0 | 0/TBD | Not started (conditional — D3) | - |

## Backlog

### Phase 999.1: Follow-up — Phase 03 deferred UAT follow-up: Test 22 (BACKLOG)

**Goal:** Resolve the UAT checkpoint deferred during Phase 03 verification
**Source phase:** 03
**Deferred at:** 2026-10-09 during /gsd-verify-work 03 session completion
**Follow-ups:**
- [ ] Test 22: pyo3 0.27 no longer auto-emits -undefined dynamic_lookup; pyo3/build.rs should call pyo3_build_config::add_extension_module_link_args() so the documented manual-build workaround links as-is again (this session injected it via RUSTFLAGS) (deferred 2026-10-09)

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
