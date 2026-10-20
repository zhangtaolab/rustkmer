# Milestones

## v1.0 Performance (Shipped: 2026-10-20)

**Phases completed:** 4 phases, 31 plans, 67 tasks

**Delivered:** CI merge gate + library hygiene (Phase 1); multi-core lock-free counting on both surfaces with exact-count differential proofs (Phase 2); bounded-memory merge + dense u64 storage (Phase 3); reproducible benchmark harness and the honest Jellyfish2 human-scale verdict (Phase 4).

**Stats:** 293 commits in range (bbac8b4..close), 26 feat commits; 373 files changed (+60,237 / −13,369); ~43,000 lines of Rust (src + pyo3/src + tests). Timeline: 2026-06-30 → 2026-10-20 (112 days).

**Closeout:** override_closeout — requirements 18/19 complete; BENCH-02 measured NO accepted as a known gap (user decision 2026-10-20). Known verification overrides: 0 newly acknowledged, 0 carried forward.

**Key accomplishments:**
- CI merge gate live on every PR (fmt / clippy `-D warnings` / test / pyo3 wheel build; 85 pre-existing warnings cleared) with library output moved to the `log` facade, `.rkdb` write consolidated to a single source of truth, and English-only strings enforced by a syn-based CJK gate (Phase 1, FOUND-01..04).
- Lock-free multi-core counting on both surfaces: DashMap sharded counter + rayon chunked parallelism, `--threads` / `RUSTKMER_THREADS` precedence chain, GIL release in `PyCounter` — with 1-vs-N differentials against committed golden baselines proving parallel counts identical to sequential (Phase 2, PCOUNT-01..04).
- The OOM-on-estimate bug that made every merge unsafe is gone: the merge planner now reads 42-byte headers instead of loading every k-mer into RAM to count them, and the budget check became a hard route rather than a suggestion.
- A merge that dies no longer takes its temporary shards with it: every merge now owns a process-unique `rustkmer-merge-<rand>/` subdir cleaned up by RAII, and whatever an aborted process could not clean up is reclaimed by a 7-day-TTL sweep on the next merge — closing the disk-exhaustion vector MERGE-03 was written about.
- The counting hot path now stores k ≤ 32 k-mers in 8-byte keys instead of 16-byte ones — half the keyed memory for the common case — while the `.rkdb` files it writes are byte-for-byte what they were before, and the public API never moved.
- `pyrustkmer.PyDatabase.merge` now takes the same memory budget and merge-strategy controls the CLI has always had — `max_memory=` and `merge_mode=`, keyword-only, validated at the Python boundary, parsed by the CLI's own parser — so a Python user's merge inherits the bounded dispatcher by construction instead of by promise.
- DENSE-01 was inverted and is now measured in the right direction: `KmerKey` is deleted so a k ≤ 32 counter really stores a 16-byte `DashMap<u64,u32>` slot, and two real 4,000,000-entry counters measure 35.66 vs 69.21 bytes/entry — ratio 0.5152, against the pre-fix 1.487.
- `KmerEntry::read_from` is now the exact inverse of `write_to`, and the two merge routes are proven to return identical, correct data for counts of 2,000,000 and 16,777,216 — the values the phase verifier showed being read back byte-swapped, with the routes disagreeing on one of them.
- WR-03 is closed: the DENSE-02 golden binary now drives `KmerCounter` -> `get_all_counts` -> `to_file_path` and compares the emitted bytes against a reference the test assembles itself, and both new write-path tests were observed RED under an injected `u64 -> u128` widening while the old committed-fixture re-hash stayed GREEN.
- A path-shaped merge entry point (`merge_databases_to_path`) whose streaming route emits `.rkdb` bytes as the merge yields them — with a chunk-derived, measurement-proven RSS bound (3,440,640 B green / 36,257,792 B red against 6,400,000 B) — plus a WR-05 overflow-proof `parse_memory_size` and both front-ends pointed at the bounded core.
- Failed prefix buckets now abort the merge loudly with their shards preserved and logged, the can-never-fire integrity tautology is replaced by two phase-independent conservation checks, concatenation is block-bounded (WR-08), and the orphan sweep reclaims loose streaming chunks (WR-04 + WR-08 + the recorded sweep gap).
- Header-only cross-input k-mer-size/canonical validation in `merge_prologue`: every merge route and both front-ends (CLI + PyDatabase.merge) now reject an incompatible input set from 42-byte header reads before any merge work or output byte.
- Record-aligned, tail-carrying, error-propagating batch reader plus an unstranding VecDeque-backed k-way merge for the prefix-cache streaming bucket strategy, with >4 MB conservation proofs red-demonstrated on the pre-fix tree and under both targeted mutations.
- The CLI merge front-end validates compatibility from 42-byte headers only (`validate_merge_compatibility`, one pass per input); the materializing loader call count in merge.rs went 6 → 0 with every rejection text preserved.
- First-4-bases (high-byte) prefix bucketing makes the prefix-cache route's index-order concatenation globally ascending, so its `sorted: true` header is truthful by construction — proven by querying the merged database through both binary-search consumers, not by inspecting the flag.
- The one-site CR-01/WR-03 fix — split_files_by_prefix stores the canonicalized bucket key and propagates canonicalization errors — makes mixed-canonical prefix-cache merges globally ascending, content-summed, and correctly queryable under a truthful header, RED-proven on both defect axes before the fix landed.
- Mixed-canonical prefix-cache merges are now ascending, summed, and exactly queryable on BOTH per-bucket writers: ExternalSortMerger::new forces the sorting (hashmap) writer for mixed-canonical header sets and merge_single_prefix_streaming refuses descending runs at record level — RED-proven on both layers, full suite 439/0.
- Stdlib-only Python harness measuring rustkmer count+merge wall-clock and peak RSS under /usr/bin/time (dual-platform parser, schema-versioned results.json, deterministic synthetic generator, full/slice/synthetic degradation ladder) with the dead perf infrastructure deleted.
- Parity gate + matched BenchmarkConfig command matrix (golden-tested, injection-screened) + interleaved counterbalanced cold-cache protocol with honest cache_state recording and a disk guardrail, all against Jellyfish2 2.3.1.
- compare.py threshold comparator (exit 0/1/2, boundary-proven 25% wall / 15% RSS, independent axes) wired into a new benchmark.yml ubuntu+macOS gate against committed per-platform baselines bootstrapped from the workflow's own CI artifacts, with the bootstrap/regeneration procedures documented in README.
- Full-scale rustkmer-vs-Jellyfish2 milestone run on CRR2044018 (3 counterbalanced reps, parity-gated, honestly cache-labeled) with its evidence committed and a mechanically rendered report whose BENCH-02 verdict is computed from the recorded medians: NO overall — k=31 YES (41-42% faster, 34% less memory), k=21 NO (jellyfish 5x faster).
- Windows-dead measurement helpers cfg-gated to their consumer (CR-02), benchmark report provenance re-rendered in a report-only commit restoring byte-identity, plus WR-08/IN-08 harness hardening riders — CI fully green at pushed HEAD including clippy (root) (windows-latest)

### Known Gaps

- **BENCH-02** (Phase 4): "rustkmer matches or beats Jellyfish2 on counting speed on CRR1936095 under fair methodology" — measured NO overall on the user-approved substitute CRR2044018: k=31 YES (494 s @ 55.2 GiB vs 843 s @ 84.0 GiB — faster and leaner), k=21 NO (~5x slower than jellyfish). Accepted as tech debt at close (user decision 2026-10-20); k=21 performance deferred to v2 (MINIM-01..03 minimizer partitioning staged; BENCH-V2-01 KMC3 comparison).
- 18 open docs/examples-level review findings from Phase 4 (0 critical remaining; CR-01/CR-02 both fixed): preserved in `milestones/v1.0-phases/04-benchmark-validation/04-REVIEW-DISPOSITION.md` for v2 triage (README positional-arg examples, mkdocs nav dead links, PyPI 404, CONTRIBUTING CI claims, etc.).
- Tech debt carried forward (full list in the milestone audit): dense u64 width on the counting table only (merge accumulator / read path stay u128 — 03-06 D7 deliberate); FASTA compressed-input gap (WR-01); merge overflow partial state (WR-02); header total_kmers counts attempts (WR-03); pyo3 data_offset clamp residual (pyo3/src/database.rs); no CI step re-renders + diffs docs/benchmark-report.md (drift risk); backlog 999.1–999.3.

---
