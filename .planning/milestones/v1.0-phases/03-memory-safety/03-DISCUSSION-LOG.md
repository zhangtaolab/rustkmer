# Phase 3: Memory Safety - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-02
**Phase:** 3-Memory Safety
**Areas discussed:** Merge budget & admission control (MERGE-01/02), In-memory merge path disposition (MERGE-01/compat), Dense storage RAM-vs-disk (DENSE-01/02), Streaming failure cleanup & interruption (MERGE-03)

**Mode:** discuss (default), with user-requested trade-off analysis + recommendation per area (analyze-overlay behavior).

---

## Merge Budget & Admission Control (MERGE-01/02)

| Option | Description | Selected |
|--------|-------------|----------|
| Fix estimation + hard route | Estimate from header `total_kmers` / file-size (not full load); keep 50%-RAM auto default + `--max-memory` override; hard-route to streaming when estimate > budget | ✓ |
| Always streaming | Route every merge to streaming regardless of size | |
| Keep soft warning | Keep current warn-and-continue (no hard enforcement) | |

**User's choice:** Fix estimation + hard route (recommended).
**Notes:** Code scout revealed `should_use_streaming()` (`format.rs:692-708`) already estimates `total_kmers × 24B` and routes, but (a) it calls `RKDatabase::from_file_path` per input to count — materializing every entry, OOMing *during the estimate*; (b) it only selects the path, no hard cap. Decision: fix estimator to read header/file-size, make the route hard. Machinery is ~90% present.

---

## In-Memory Merge Path Disposition (MERGE-01/compat)

| Option | Description | Selected |
|--------|-------------|----------|
| Keep behind flag | Retain `merge_databases_inmemory` behind explicit `--merge-mode memory` + auto-small; streaming is safe default; memory mode rejects/warns when over budget | ✓ |
| Remove entirely | Delete the in-memory path; all merges stream | |
| Keep current default | Leave small-input default as in-memory (status quo) | |

**User's choice:** Keep behind flag (recommended).
**Notes:** `--merge-mode auto|memory|streaming` already exists. Removing the in-memory path breaks existing `--merge-mode memory` callers for no milestone benefit; bounding it (D-01 hard-route) satisfies MERGE-01 while keeping a useful small-input fast path.

---

## Dense Storage: RAM-only vs On-Disk (DENSE-01/02)

| Option | Description | Selected |
|--------|-------------|----------|
| RAM-only u64 | Counter/in-memory merge use u64 keys for k ≤ 32; `.rkdb` v2 disk stays 16-byte u128; golden fixtures survive; disk-dense deferred to v2 | ✓ |
| RAM + disk u64 | Also pack u64 on disk (v2 dense flag or v3); saves disk but breaks 20-byte layout, invalidates golden sha256, needs migration | |
| Defer to Phase 4 | Decide after benchmarking whether RAM-only meets the budget | |

**User's choice:** RAM-only u64 (recommended).
**Notes:** REQUIREMENTS targets "halving **counting memory**" (RAM). PROJECT.md mandates preserving `.rkdb` v2 unless a perf win justifies a breaking change — disk savings don't clear that bar this milestone. RAM-only u64 satisfies the goal with zero format risk and keeps Phase 1/2 golden baselines valid. On-disk dense explicitly deferred to v2 (this deferral *is* the DENSE-02 "surface the tradeoff" obligation). Key correctness lock: u64 vs u128 verification is at the decoded (kmer-string, count) level, not raw-integer (the two widths pack the same k-mer to different bit positions).

---

## Streaming Failure Cleanup & Interruption (MERGE-03)

| Option | Description | Selected |
|--------|-------------|----------|
| RAII + process dir + startup sweep | Add RAII to prefix-cache path; shards under `rustkmer-merge-<pid>-<rand>/`; startup stale-shard sweep; no signal handler; failed merge = clean restart | ✓ |
| Add signal handler | Also install `ctrlc` handler for graceful Ctrl-C cleanup | |
| RAII only | Just add RAII to prefix-cache path | |

**User's choice:** RAII + process-unique subdir + startup stale-shard sweep (recommended).
**Notes:** Streaming path already has RAII (`TempFileManager`/`StreamingMergeIterator::Drop`); prefix-cache path does NOT (manual `remove_file` on success only, `prefix_cache_merge.rs:322-326`). Critical insight: release profile has `panic = "abort"`, and default `SIGTERM`/`SIGINT`/`SIGKILL` handlers terminate without unwinding — so RAII `Drop` does NOT run on abort/kill. The process-unique subdir + startup sweep is therefore the real defense against disk exhaustion, not RAII alone. No signal handler (scope creep + soundness). Not resumable (v2). Closes the CONCERNS.md "streaming error paths untested" gap.

---

## Claude's Discretion

The following were marked as planner/researcher discretion (no user lock needed):
- `PackedKmer` concrete representation (enum vs parallel type vs generic) — constrained by public-API stability.
- Estimator source (header `total_kmers` vs `file_size / 20` vs fallback) — as long as it does not load entries.
- Startup-sweep orphan detection (PID-liveness vs age-based TTL).
- `memory`-mode over-budget behavior (reject vs loud-warn).
- Whether dense u64 extends to the read/query path (default: no — out of scope unless zero-cost).
- Exact `PyDatabase.merge` kwarg shape for budget/strategy (must route through the bounded core).

## Carry-Forward (locked from prior phases, not re-asked)

- Public API stability for `KmerCounter`/`KmerEntry` (Phase 2 D-05).
- Golden-capture-first sequencing — reuse existing Phase 1/2 u128 golden baselines (Phase 1 D-10).
- Coverage matrix `k ∈ {21,32,64}` × canonical × sorted (Phase 1 D-13).
- `u128`-vs-`u64` differential as the DENSE-03 correctness tool (analog to Phase 2 D-10's 1-vs-N differential).
- Mixed-k merge rejected (existing `KmerCounter::merge` behavior).

## Deferred Ideas

- On-disk dense `u64` packing (v2 dense flag or v3) + migration path — v2 (DENSE-02 tradeoff surfaced).
- Adaptive 5-/6-prefix shard granularity (MINIM-03) — v2.
- Resumable streaming merge — v2.
- Signal-handler-based Ctrl-C cleanup — v2 (soundness).
- Minimizer/signature-partitioned bounded-memory counting (MINIM-01/02) — v2.
- Configurable counter width / saturation warning (SAT-01/02) — v2.
- Dense u64 on the query/read path — out of scope unless zero-cost.
